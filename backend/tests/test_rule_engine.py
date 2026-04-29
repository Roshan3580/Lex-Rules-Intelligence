"""Unit tests for deterministic rule enforcement (no LLM)."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app import models
from app.services import rule_engine


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def _rule(**kwargs):
    defaults = dict(
        state="California",
        tax_category="sales_tax",
        rule_title="Demo rule",
        rule_summary="Summary for tests",
        review_status="published",
        confidence_score=0.9,
    )
    defaults.update(kwargs)
    return models.Rule(**defaults)


def test_normalize_state_abbr():
    assert rule_engine.normalize_state("CA") == "California"
    assert rule_engine.normalize_state("ca") == "California"


def test_condition_equals_and_violation(db_session):
    r = _rule(
        workflow_stage="submission",
        condition_logic=json.dumps(
            {"op": "equals", "field": "entity_type", "value": "LLC"}
        ),
        required_documentation=["Form XYZ"],
    )
    db_session.add(r)
    db_session.commit()

    out = rule_engine.validate_submission(
        db_session,
        state="CA",
        tax_category="sales_tax",
        workflow_stage="submission",
        payload={"entity_type": "LLC", "documents": []},
    )
    assert out["valid"] is False
    assert out["risk_level"] == "high"
    assert len(out["violations"]) >= 1
    assert any("Form XYZ" in v["reason"] for v in out["violations"])


def test_condition_not_applied_wrong_entity(db_session):
    r = _rule(
        workflow_stage="submission",
        condition_logic=json.dumps(
            {"op": "equals", "field": "entity_type", "value": "LLC"}
        ),
        required_documentation=["Form XYZ"],
    )
    db_session.add(r)
    db_session.commit()

    out = rule_engine.validate_submission(
        db_session,
        state="California",
        tax_category="sales_tax",
        workflow_stage="submission",
        payload={"entity_type": "Corp", "documents": []},
    )
    assert out["valid"] is True
    assert out["violations"] == []


def test_greater_than_threshold(db_session):
    r = _rule(
        workflow_stage="submission",
        condition_logic=json.dumps(
            {"op": "greater_than", "field": "amount", "value": 10000}
        ),
        required_forms=["Schedule R"],
    )
    db_session.add(r)
    db_session.commit()

    out = rule_engine.validate_submission(
        db_session,
        state="California",
        tax_category="sales_tax",
        workflow_stage="submission",
        payload={"amount": 50_000, "documents": []},
    )
    assert out["valid"] is False
    assert any("Schedule R" in v["reason"] for v in out["violations"])


def test_malformed_condition_skipped_with_warning(db_session):
    r = _rule(
        workflow_stage="submission",
        condition_logic='{"invalid json',
        required_documentation=["ZZZ"],
    )
    db_session.add(r)
    db_session.commit()

    rules, warns = rule_engine.get_applicable_rules(
        db_session,
        state="California",
        tax_category="sales_tax",
        workflow_stage="submission",
    )
    assert rules == []
    assert any("malformed" in w for w in warns)


def test_draft_rules_not_enforced(db_session):
    r = _rule(
        review_status="draft",
        required_documentation=["Secret Form"],
    )
    db_session.add(r)
    db_session.commit()

    out = rule_engine.validate_submission(
        db_session,
        state="CA",
        tax_category="sales_tax",
        payload={"documents": []},
    )
    assert out["valid"] is True
