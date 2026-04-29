"""Audit trail read API."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal, init_db
from app.main import app
from app import models
from app.services import audit_service


@pytest.fixture(autouse=True)
def _db():
    init_db()


def test_viewer_cannot_get_audit():
    client = TestClient(app)
    res = client.get("/api/audit", headers={"X-User-Role": "viewer"})
    assert res.status_code == 403


def test_reviewer_can_get_audit():
    client = TestClient(app)
    res = client.get("/api/audit", headers={"X-User-Role": "reviewer"})
    assert res.status_code == 200
    body = res.json()
    assert "logs" in body and "total" in body
    assert isinstance(body["logs"], list)


def test_audit_list_newest_first():
    et = f"ordering_test_{uuid.uuid4().hex[:10]}"
    ta = datetime.utcnow() - timedelta(hours=2)
    tb = datetime.utcnow() - timedelta(hours=1)

    db = SessionLocal()
    try:
        older = models.AuditLogEntry(
            action="old_row",
            resource_type=et,
            detail={},
            tenant_id="default",
            created_at=ta,
        )
        newer = models.AuditLogEntry(
            action="new_row",
            resource_type=et,
            detail={},
            tenant_id="default",
            created_at=tb,
        )
        db.add(older)
        db.add(newer)
        db.commit()
    finally:
        db.close()

    db = SessionLocal()
    try:
        rows, _total = audit_service.list_audit_logs(
            db, entity_type=et, limit=50, offset=0
        )
        assert len(rows) >= 2
        assert rows[0].action == "new_row"
        assert rows[1].action == "old_row"
        ts = [r.created_at for r in rows[:2]]
        assert ts == sorted(ts, reverse=True)
    finally:
        db.close()


def test_audit_limit_constant():
    assert audit_service.AUDIT_LIST_MAX_LIMIT == 500

