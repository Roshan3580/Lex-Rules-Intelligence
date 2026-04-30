"""Header-based tenant scoping (demo isolation)."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app import models
from app.database import SessionLocal, init_db
from app.main import app


@pytest.fixture(autouse=True)
def _ensure_db_tables():
    init_db()


def test_missing_tenant_header_defaults_to_default_for_rule_listing():
    with SessionLocal() as db:
        a = models.Rule(
            tenant_id="default",
            state="California",
            tax_category="sales_tax",
            rule_title="Default tenant rule",
            rule_summary="x",
            review_status="published",
            confidence_score=0.9,
        )
        b = models.Rule(
            tenant_id="demo-client-a",
            state="California",
            tax_category="sales_tax",
            rule_title="Other tenant rule",
            rule_summary="x",
            review_status="published",
            confidence_score=0.9,
        )
        db.add(a)
        db.add(b)
        db.commit()
        a_id = a.id
        b_id = b.id

    client = TestClient(app)
    res = client.get("/api/rules")  # no X-Tenant-Id
    assert res.status_code == 200
    ids = {r["id"] for r in res.json()}
    assert a_id in ids
    assert b_id not in ids


def test_invalid_tenant_id_returns_400():
    client = TestClient(app)
    res = client.get(
        "/api/rules",
        headers={"X-Tenant-Id": "bad tenant id", "X-User-Role": "viewer"},
    )
    assert res.status_code == 400
    body = res.json()
    assert body["detail"]["error"] == "invalid_tenant_id"


def test_tenant_isolation_rules_list_and_detail():
    with SessionLocal() as db:
        a = models.Rule(
            tenant_id="demo-client-a",
            state="California",
            tax_category="sales_tax",
            rule_title="Tenant A rule",
            rule_summary="x",
            review_status="published",
            confidence_score=0.9,
        )
        b = models.Rule(
            tenant_id="demo-client-b",
            state="California",
            tax_category="sales_tax",
            rule_title="Tenant B rule",
            rule_summary="x",
            review_status="published",
            confidence_score=0.9,
        )
        db.add(a)
        db.add(b)
        db.commit()
        a_id = a.id
        b_id = b.id

    client = TestClient(app)
    res_a = client.get("/api/rules", headers={"X-Tenant-Id": "demo-client-a"})
    assert res_a.status_code == 200
    ids_a = {r["id"] for r in res_a.json()}
    assert a_id in ids_a
    assert b_id not in ids_a

    res_b_detail = client.get(
        f"/api/rules/{b_id}", headers={"X-Tenant-Id": "demo-client-a"}
    )
    assert res_b_detail.status_code == 404


def test_validate_submission_scopes_rules_by_tenant():
    # Rule exists only in tenant B; tenant A validation should not see it.
    with SessionLocal() as db:
        db.add(
            models.Rule(
                tenant_id="demo-client-b",
                state="California",
                tax_category="sales_tax",
                workflow_stage="submission",
                rule_title="Tenant B enforcement rule",
                rule_summary="x",
                review_status="published",
                confidence_score=0.9,
                condition_logic=json.dumps(
                    {"op": "equals", "field": "entity_type", "value": "LLC"}
                ),
                required_documentation=["Form B-1"],
            )
        )
        db.commit()

    client = TestClient(app)
    res = client.post(
        "/api/validate-submission",
        json={
            "state": "CA",
            "tax_category": "sales_tax",
            "workflow_stage": "submission",
            "payload": {"entity_type": "LLC", "documents": []},
        },
        headers={"X-Tenant-Id": "demo-client-a"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["valid"] is True


def test_webhook_subscriptions_are_tenant_scoped():
    with SessionLocal() as db:
        db.add(
            models.WebhookSubscription(
                tenant_id="demo-client-a",
                url="https://example.com/a",
                events=["*"],
                secret_hint="aaaa",
                signing_secret="secret-a",
                active=True,
            )
        )
        db.add(
            models.WebhookSubscription(
                tenant_id="demo-client-b",
                url="https://example.com/b",
                events=["*"],
                secret_hint="bbbb",
                signing_secret="secret-b",
                active=True,
            )
        )
        db.commit()

    client = TestClient(app)
    res = client.get("/api/webhooks/subscriptions", headers={"X-Tenant-Id": "demo-client-a"})
    assert res.status_code == 200
    urls = {r["url"] for r in res.json()}
    assert urls == {"https://example.com/a"}


def test_audit_list_is_tenant_scoped():
    with SessionLocal() as db:
        db.add(
            models.AuditLogEntry(
                action="tenant_a_action",
                resource_type="test",
                detail={},
                tenant_id="demo-client-a",
            )
        )
        db.add(
            models.AuditLogEntry(
                action="tenant_b_action",
                resource_type="test",
                detail={},
                tenant_id="demo-client-b",
            )
        )
        db.commit()

    client = TestClient(app)
    res = client.get("/api/audit", headers={"X-User-Role": "reviewer", "X-Tenant-Id": "demo-client-a"})
    assert res.status_code == 200
    actions = {r["action"] for r in res.json()["logs"]}
    assert "tenant_a_action" in actions
    assert "tenant_b_action" not in actions

