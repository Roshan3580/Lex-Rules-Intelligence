"""Strict publish readiness + enforcement diagnostics."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import models
from app.config import settings
from app.database import SessionLocal, init_db
from app.main import app


@pytest.fixture(autouse=True)
def _ensure_db_tables():
    init_db()


@pytest.fixture(autouse=True)
def _disable_webhook_background_jobs(monkeypatch):
    """Avoid slow network/backoff in publish tests."""
    import app.services.webhook_delivery_service as wds

    monkeypatch.setattr(wds, "schedule_send_event", lambda *args, **kwargs: None)


def _make_rule(*, approved: bool, effective_date: str | None, condition_logic: str | None):
    return models.Rule(
        state="California",
        tax_category="sales_tax",
        rule_title="Test rule",
        rule_summary="A sufficiently long summary for validation.",
        review_status="approved" if approved else "needs_review",
        confidence_score=0.9,
        workflow_stage="submission",
        required_actions=["File return"],
        source_url="https://example.com/source",
        source_document_name="Doc",
        source_snippet="Verbatim evidence snippet that is long enough to count.",
        effective_date=effective_date,
        condition_logic=condition_logic,
        tenant_id="default",
    )


def test_publish_readiness_runs_when_strict_false(monkeypatch):
    monkeypatch.setattr(settings, "strict_publish_checks", False)
    with SessionLocal() as db:
        r = _make_rule(approved=True, effective_date=None, condition_logic=None)
        db.add(r)
        db.commit()
        rid = r.id

    client = TestClient(app)
    res = client.get(
        f"/api/rules/{rid}/publish-readiness",
        headers={"X-User-Role": "reviewer"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["rule_id"] == rid
    assert body["strict_mode_enabled"] is False
    assert any(b["code"] == "missing_effective_date" for b in body["blockers"])


def test_viewer_cannot_call_publish_readiness(monkeypatch):
    monkeypatch.setattr(settings, "strict_publish_checks", False)
    with SessionLocal() as db:
        r = _make_rule(approved=True, effective_date=None, condition_logic=None)
        db.add(r)
        db.commit()
        rid = r.id
    client = TestClient(app)
    res = client.get(
        f"/api/rules/{rid}/publish-readiness",
        headers={"X-User-Role": "viewer"},
    )
    assert res.status_code == 403


def test_strict_mode_true_blocks_publish_with_structured_blockers(monkeypatch):
    monkeypatch.setattr(settings, "strict_publish_checks", True)
    with SessionLocal() as db:
        r = _make_rule(approved=True, effective_date=None, condition_logic=None)
        db.add(r)
        db.commit()
        rid = r.id

    client = TestClient(app)
    res = client.post(
        f"/api/review/rules/{rid}/action",
        json={"action": "publish"},
        headers={"X-User-Role": "reviewer"},
    )
    assert res.status_code == 422
    detail = res.json()["detail"]
    assert detail["error"] == "publish_blocked"
    assert any(b["code"] == "missing_effective_date" for b in detail["blockers"])


def test_strict_mode_false_preserves_permissive_publish(monkeypatch):
    monkeypatch.setattr(settings, "strict_publish_checks", False)
    with SessionLocal() as db:
        r = _make_rule(approved=True, effective_date=None, condition_logic=None)
        db.add(r)
        db.commit()
        rid = r.id

    client = TestClient(app)
    res = client.post(
        f"/api/review/rules/{rid}/action",
        json={"action": "publish"},
        headers={"X-User-Role": "reviewer"},
    )
    assert res.status_code == 200
    assert res.json()["review_status"] == "published"


def test_malformed_condition_logic_creates_blocker(monkeypatch):
    monkeypatch.setattr(settings, "strict_publish_checks", True)
    with SessionLocal() as db:
        r = _make_rule(approved=True, effective_date="2026-01-01", condition_logic='{"oops"')
        db.add(r)
        db.commit()
        rid = r.id
    client = TestClient(app)
    res = client.get(
        f"/api/rules/{rid}/publish-readiness",
        headers={"X-User-Role": "reviewer"},
    )
    assert res.status_code == 200
    body = res.json()
    assert any(b["code"] == "malformed_condition_logic" for b in body["blockers"])
