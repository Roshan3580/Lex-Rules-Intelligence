"""Tenant isolation for operational metrics and ingestion history."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import models
from app.database import SessionLocal, init_db
from app.main import app


@pytest.fixture(autouse=True)
def _ensure_db_tables():
    init_db()


def test_ingestion_runs_are_tenant_scoped_list_and_detail():
    with SessionLocal() as db:
        run_a = models.IngestionRun(kind="yaml", status="completed", tenant_id="demo-client-a")
        run_b = models.IngestionRun(kind="yaml", status="completed", tenant_id="demo-client-b")
        db.add(run_a)
        db.add(run_b)
        db.flush()
        db.add(
            models.IngestionRunItem(
                run_id=run_a.id,
                tenant_id="demo-client-a",
                name="A",
                status="ingested",
            )
        )
        db.add(
            models.IngestionRunItem(
                run_id=run_b.id,
                tenant_id="demo-client-b",
                name="B",
                status="ingested",
            )
        )
        db.commit()
        a_id = run_a.id
        b_id = run_b.id

    client = TestClient(app)
    res = client.get("/api/ingest/runs", headers={"X-Tenant-Id": "demo-client-a"})
    assert res.status_code == 200
    ids = {r["id"] for r in res.json()}
    assert a_id in ids
    assert b_id not in ids

    res_other = client.get(
        f"/api/ingest/runs/{b_id}", headers={"X-Tenant-Id": "demo-client-a"}
    )
    assert res_other.status_code == 404

    res_detail = client.get(
        f"/api/ingest/runs/{a_id}", headers={"X-Tenant-Id": "demo-client-a"}
    )
    assert res_detail.status_code == 200
    body = res_detail.json()
    assert body["id"] == a_id
    assert len(body["items"]) == 1
    assert body["items"][0]["name"] == "A"


def test_dashboard_kpis_tenant_scoped():
    with SessionLocal() as db:
        db.add(
            models.Rule(
                tenant_id="demo-client-a",
                state="California",
                tax_category="sales_tax",
                rule_title="A",
                rule_summary="x",
                review_status="published",
                confidence_score=0.9,
            )
        )
        db.add(
            models.Rule(
                tenant_id="demo-client-b",
                state="California",
                tax_category="sales_tax",
                rule_title="B",
                rule_summary="x",
                review_status="published",
                confidence_score=0.9,
            )
        )
        db.commit()

    client = TestClient(app)
    res = client.get("/api/dashboard", headers={"X-Tenant-Id": "demo-client-a"})
    assert res.status_code == 200
    kpis = res.json()["kpis"]
    assert kpis["total_rules"] >= 1


def test_rejection_coverage_tenant_scoped():
    with SessionLocal() as db:
        db.add(
            models.OutcomeEvent(
                tenant_id="demo-client-a",
                submission_id=None,
                state="California",
                tax_category="sales_tax",
                workflow_stage="submission",
                rejection_reason="A reason",
                rejection_code=None,
                normalized_root_cause="A",
                payload={},
                matched_rule_ids=None,
                coverage_status="missing_rule",
            )
        )
        db.add(
            models.OutcomeEvent(
                tenant_id="demo-client-b",
                submission_id=None,
                state="California",
                tax_category="sales_tax",
                workflow_stage="submission",
                rejection_reason="B reason",
                rejection_code=None,
                normalized_root_cause="B",
                payload={},
                matched_rule_ids=None,
                coverage_status="missing_rule",
            )
        )
        db.commit()

    client = TestClient(app)
    res = client.get(
        "/api/analytics/rejection-coverage", headers={"X-Tenant-Id": "demo-client-a"}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["total_outcomes"] == 1


def test_platform_kpis_tenant_scoped():
    with SessionLocal() as db:
        db.add(
            models.Rule(
                tenant_id="demo-client-a",
                state="California",
                tax_category="sales_tax",
                rule_title="A",
                rule_summary="x",
                review_status="published",
                confidence_score=0.9,
            )
        )
        db.add(
            models.Source(
                tenant_id="demo-client-a",
                source_type="url",
                name="S",
                url="https://example.com",
                status="processed",
                checksum="x",
            )
        )
        db.commit()

    client = TestClient(app)
    res = client.get("/api/platform/kpis", headers={"X-Tenant-Id": "demo-client-a"})
    assert res.status_code == 200
    data = res.json()
    assert data["rules_published"] >= 1
    assert data["active_sources"] >= 1


def test_cache_endpoint_labels_process_level_stats():
    client = TestClient(app)
    res = client.get("/api/platform/cache", headers={"X-User-Role": "reviewer"})
    assert res.status_code == 200
    body = res.json()
    assert body.get("global_process_cache_stats") is True

