"""Backfill canonical FKs + platform RBAC."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base
from app.main import app
from app import models
from app.services import backfill_service


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


def test_canonical_consistency_counts(db_session):
    r = models.Rule(
        state="CA",
        tax_category="sales_tax",
        rule_title="t",
        rule_summary="s",
        review_status="draft",
        confidence_score=0.5,
        program_variant={"tax_program": "sales_tax"},
        tenant_id="default",
    )
    db_session.add(r)
    db_session.commit()
    rep = backfill_service.canonical_consistency_report(db_session)
    assert rep["total_rules"] == 1
    assert rep["rules_missing_jurisdiction_id"] == 1
    assert rep["rules_missing_program_variant_ref_id"] == 1
    assert rep["rules_with_legacy_program_variant_but_no_fk"] == 1


def test_backfill_jurisdictions_dry_then_apply(db_session):
    r = models.Rule(
        state="TX",
        tax_category="general_tax",
        rule_title="t",
        rule_summary="s",
        review_status="published",
        confidence_score=0.9,
    )
    db_session.add(r)
    db_session.commit()
    jid_before = db_session.query(models.Jurisdiction).count()
    _, sm = backfill_service.backfill_jurisdictions(db_session, dry_run=True)
    db_session.commit()
    assert jid_before == db_session.query(models.Jurisdiction).count()
    assert sm["jurisdictions_updated"] == 0
    _, sm2 = backfill_service.backfill_jurisdictions(db_session, dry_run=False)
    db_session.commit()
    db_session.refresh(r)
    assert r.jurisdiction_id is not None
    assert sm2["jurisdictions_updated"] >= 1
    jid_after_first = db_session.query(models.Jurisdiction).count()
    _, sm3 = backfill_service.backfill_jurisdictions(db_session, dry_run=False)
    db_session.commit()
    assert sm3["jurisdictions_updated"] == 0
    assert db_session.query(models.Jurisdiction).count() == jid_after_first


def test_rejection_links_idempotent(db_session):
    pv = {"rejection_reason_map": {"XCODE": "label"}}
    r = models.Rule(
        state="California",
        tax_category="sales_tax",
        rule_title="t",
        rule_summary="s",
        review_status="published",
        confidence_score=0.9,
        program_variant=pv,
    )
    db_session.add(r)
    db_session.flush()
    backfill_service.sync_canonical_fields_for_new_rule(db_session, r)
    db_session.commit()
    lc1 = db_session.query(models.RuleRejectionLink).count()
    backfill_service.backfill_rejection_links(db_session, dry_run=False)
    db_session.commit()
    lc2 = db_session.query(models.RuleRejectionLink).count()
    assert lc2 == lc1


@pytest.mark.parametrize(
    "path,headers,expect",
    [
        ("/api/platform/canonical-report", {"X-User-Role": "viewer"}, 403),
        ("/api/platform/canonical-report", {"X-User-Role": "reviewer"}, 200),
        ("/api/platform/backfill", {"X-User-Role": "viewer"}, 403),
        ("/api/platform/backfill", {"X-User-Role": "reviewer"}, 200),
        ("/api/platform/backfill", {"X-User-Role": "admin"}, 200),
    ],
)
def test_platform_rbac_canonical(path, headers, expect):
    client = TestClient(app)
    method = client.get if path.endswith("canonical-report") else client.post
    kwargs: dict = {"headers": headers}
    if path.endswith("backfill"):
        kwargs["json"] = {"target": "all", "dry_run": True}
    res = method(path, **kwargs)
    assert res.status_code == expect


def test_reviewer_cannot_apply_canonical_backfill():
    client = TestClient(app)
    res = client.post(
        "/api/platform/backfill",
        json={"target": "all", "dry_run": False},
        headers={"X-User-Role": "reviewer"},
    )
    assert res.status_code == 403
