"""RBAC for platform cache introspection endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from app.services.cache_service import default_cache, make_key, NAMESPACE_VALIDATION


@pytest.fixture(autouse=True)
def _ensure_db_tables():
    init_db()


def test_cache_get_viewer_forbidden():
    client = TestClient(app)
    res = client.get("/api/platform/cache", headers={"X-User-Role": "viewer"})
    assert res.status_code == 403
    assert res.json()["detail"]["error"] == "forbidden"


def test_cache_get_reviewer_ok():
    client = TestClient(app)
    res = client.get("/api/platform/cache", headers={"X-User-Role": "reviewer"})
    assert res.status_code == 200
    data = res.json()
    assert "namespaces" in data
    assert "rule_lookup" in data["namespaces"]
    assert "validation" in data["namespaces"]


def test_cache_clear_reviewer_forbidden():
    client = TestClient(app)
    res = client.post(
        "/api/platform/cache/clear",
        json={},
        headers={"X-User-Role": "reviewer"},
    )
    assert res.status_code == 403


def test_cache_clear_admin_ok_and_clears_validation():
    default_cache().set(make_key(NAMESPACE_VALIDATION, "e" * 64), {"x": 1}, 60)
    client = TestClient(app)
    res = client.post(
        "/api/platform/cache/clear",
        json={},
        headers={"X-User-Role": "admin"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    st = default_cache().stats()
    assert st[NAMESPACE_VALIDATION]["current_size"] == 0
