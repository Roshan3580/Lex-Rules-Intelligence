"""Webhook resend + health endpoints (mocked outbound HTTP)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal, init_db
from app.main import app
from app import models


@pytest.fixture(autouse=True)
def _ensure_db_tables():
    init_db()


class _FakeResp:
    def __init__(self, status_code: int, text: str = "ok"):
        self.status_code = status_code
        self.text = text


class _FakeClient:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, content=None, headers=None):
        return _FakeResp(200, "ok")


def test_viewer_cannot_access_webhook_health():
    client = TestClient(app)
    res = client.get("/api/webhooks/health", headers={"X-User-Role": "viewer"})
    assert res.status_code == 403


def test_reviewer_can_access_webhook_health_and_no_secret():
    with SessionLocal() as db:
        db.add(
            models.WebhookSubscription(
                tenant_id="default",
                url="https://example.com/hook",
                events=["*"],
                secret_hint="abcd1234",
                signing_secret="super-secret",
                active=True,
            )
        )
        db.commit()
    client = TestClient(app)
    res = client.get("/api/webhooks/health", headers={"X-User-Role": "reviewer"})
    assert res.status_code == 200
    body = res.json()
    assert "signing_secret" not in str(body).lower()


def test_viewer_and_reviewer_cannot_resend():
    client = TestClient(app)
    res = client.post(
        "/api/webhooks/deliveries/nope/resend", headers={"X-User-Role": "viewer"}
    )
    assert res.status_code == 403
    res2 = client.post(
        "/api/webhooks/deliveries/nope/resend", headers={"X-User-Role": "reviewer"}
    )
    assert res2.status_code == 403


def test_admin_can_resend_creates_new_attempt(monkeypatch):
    # mock outbound httpx client
    import app.services.webhook_delivery_service as wds

    monkeypatch.setattr(wds.httpx, "Client", _FakeClient)

    with SessionLocal() as db:
        sub = models.WebhookSubscription(
            tenant_id="default",
            url="https://example.com/hook",
            events=["*"],
            secret_hint="abcd1234",
            signing_secret="super-secret",
            active=True,
        )
        db.add(sub)
        db.flush()
        old = models.WebhookDeliveryAttempt(
            subscription_id=sub.id,
            event_type="submission.validated",
            payload={"event": "submission.validated", "data": {"x": 1}},
            status="failed",
            attempt_count=3,
            last_error="boom",
            created_at=datetime.utcnow() - timedelta(hours=1),
        )
        db.add(old)
        db.commit()
        old_id = old.id

    client = TestClient(app)
    res = client.post(
        f"/api/webhooks/deliveries/{old_id}/resend",
        headers={"X-User-Role": "admin"},
    )
    assert res.status_code == 200
    new = res.json()
    assert new["id"] != old_id
    assert new["subscription_id"]
    assert new["event_type"] == "submission.validated"
    assert new["attempt_count"] >= 1
    assert new["status"] in ("success", "failed", "pending")

    with SessionLocal() as db:
        n = (
            db.query(models.WebhookDeliveryAttempt)
            .filter(models.WebhookDeliveryAttempt.subscription_id == new["subscription_id"])
            .count()
        )
        assert n >= 2


def test_resend_inactive_subscription_400(monkeypatch):
    import app.services.webhook_delivery_service as wds

    monkeypatch.setattr(wds.httpx, "Client", _FakeClient)

    with SessionLocal() as db:
        sub = models.WebhookSubscription(
            tenant_id="default",
            url="https://example.com/hook",
            events=["*"],
            secret_hint="abcd1234",
            signing_secret="super-secret",
            active=False,
        )
        db.add(sub)
        db.flush()
        old = models.WebhookDeliveryAttempt(
            subscription_id=sub.id,
            event_type="submission.validated",
            payload={"event": "submission.validated", "data": {"x": 1}},
            status="failed",
            attempt_count=1,
            last_error="boom",
        )
        db.add(old)
        db.commit()
        old_id = old.id

    client = TestClient(app)
    res = client.post(
        f"/api/webhooks/deliveries/{old_id}/resend",
        headers={"X-User-Role": "admin"},
    )
    assert res.status_code == 400
    body = res.json()
    assert body["detail"]["error"] == "invalid_delivery"
