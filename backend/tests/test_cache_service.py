"""Unit tests for in-process TTL cache + enforcement invalidation hook."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app import models
from app.services import rule_engine
from app.services.cache_service import (
    NAMESPACE_RULE_LOOKUP,
    NAMESPACE_VALIDATION,
    TTLCacheService,
    default_cache,
    invalidate_enforcement_caches,
    make_key,
)


@pytest.fixture
def fresh_cache():
    import app.services.cache_service as cs

    c = TTLCacheService()
    old = cs._cache
    cs._cache = c
    try:
        yield c
    finally:
        cs._cache = old


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


def test_ttl_get_set_clear_namespace_stats(fresh_cache: TTLCacheService):
    k = make_key(NAMESPACE_RULE_LOOKUP, "a" * 64)
    assert fresh_cache.get(k) is None
    fresh_cache.set(k, {"x": 1}, ttl_seconds=120)
    assert fresh_cache.get(k) == {"x": 1}
    fresh_cache.clear_namespace(NAMESPACE_RULE_LOOKUP)
    assert fresh_cache.get(k) is None
    st = fresh_cache.stats()
    assert st[NAMESPACE_RULE_LOOKUP]["invalidations"] >= 1


def test_invalidate_enforcement_caches_clears_both(monkeypatch):
    import app.services.cache_service as cs

    c = TTLCacheService()
    monkeypatch.setattr(cs, "_cache", c)
    c.set(make_key(NAMESPACE_RULE_LOOKUP, "b" * 64), [1], 120)
    c.set(make_key(NAMESPACE_VALIDATION, "c" * 64), {"ok": True}, 60)
    invalidate_enforcement_caches()
    st = c.stats()
    assert st[NAMESPACE_RULE_LOOKUP]["current_size"] == 0
    assert st[NAMESPACE_VALIDATION]["current_size"] == 0


def test_validation_cache_hit_on_second_call(db_session, fresh_cache: TTLCacheService):
    r = models.Rule(
        state="California",
        tax_category="sales_tax",
        rule_title="t",
        rule_summary="s",
        review_status="published",
        confidence_score=0.95,
        workflow_stage="submission",
        condition_logic=json.dumps(
            {"op": "equals", "field": "entity_type", "value": "LLC"}
        ),
        required_documentation=["Form XYZ"],
    )
    db_session.add(r)
    db_session.commit()

    payload = {"entity_type": "LLC", "documents": []}
    rule_engine.validate_submission(
        db_session,
        state="CA",
        tax_category="sales_tax",
        workflow_stage="submission",
        payload=payload,
    )
    s1 = fresh_cache.stats()[NAMESPACE_VALIDATION]["misses"]
    rule_engine.validate_submission(
        db_session,
        state="CA",
        tax_category="sales_tax",
        workflow_stage="submission",
        payload=payload,
    )
    h2 = fresh_cache.stats()[NAMESPACE_VALIDATION]["hits"]
    assert h2 >= 1
    assert fresh_cache.stats()[NAMESPACE_VALIDATION]["misses"] == s1


def test_clear_all_resets_entries_and_increments_invalidations(fresh_cache: TTLCacheService):
    fresh_cache.set(make_key(NAMESPACE_VALIDATION, "d" * 64), {"a": 1}, 60)
    fresh_cache.clear_all()
    st = fresh_cache.stats()
    assert st[NAMESPACE_VALIDATION]["current_size"] == 0
    assert st[NAMESPACE_VALIDATION]["invalidations"] >= 1


def test_default_cache_singleton():
    assert default_cache() is default_cache()
