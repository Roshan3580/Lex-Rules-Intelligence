"""RBAC middleware and require_role dependency."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.database import init_db
from app.main import app
from app.middleware.rbac import require_role


@pytest.fixture(autouse=True)
def _ensure_db_tables():
    init_db()


def _make_request_with_state(
    role: str | None, user_id: str | None = None
) -> Request:
    hdrs: list[tuple[bytes, bytes]] = []
    if role is not None:
        hdrs.append((b"x-user-role", role.encode()))
    if user_id is not None:
        hdrs.append((b"x-user-id", user_id.encode()))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.1"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/dummy",
        "raw_path": b"/dummy",
        "query_string": b"",
        "headers": hdrs,
        "client": ("127.0.0.1", 1234),
        "server": ("127.0.0.1", 8000),
    }
    req = Request(scope)
    # Simulate RBACMiddleware assigning state
    if role is None:
        req.state.user_role = "viewer"
    else:
        raw = role.strip().lower()
        req.state.user_role = (
            raw if raw in {"admin", "reviewer", "viewer"} else "viewer"
        )
    req.state.user_id = ((user_id or "").strip()) or "demo-user"
    return req


def test_require_role_allows_member():
    dep = require_role("reviewer")
    req = _make_request_with_state("reviewer")
    assert dep(req) == "reviewer"


def test_require_role_admin_bypasses_reviewers():
    dep = require_role("reviewer")
    req = _make_request_with_state("admin")
    assert dep(req) == "admin"


def test_require_role_denies_viewer_for_admin_only():
    dep = require_role("admin")
    req = _make_request_with_state("viewer")
    with pytest.raises(HTTPException) as exc:
        dep(req)
    assert exc.value.status_code == 403
    detail = exc.value.detail
    assert detail["error"] == "forbidden"
    assert detail["current_role"] == "viewer"


def test_client_viewer_cannot_register_webhook():
    client = TestClient(app)
    payload = {"url": "https://example.com/hook"}
    res = client.post(
        "/api/webhooks/register",
        json=payload,
        headers={"X-User-Role": "viewer"},
    )
    assert res.status_code == 403
    body = res.json()
    assert body["detail"]["error"] == "forbidden"


def test_client_missing_role_header_defaults_like_viewer_for_admin_route():
    client = TestClient(app)
    payload = {"url": "https://example.com/hook"}
    res = client.post("/api/webhooks/register", json=payload)
    assert res.status_code == 403


def test_client_admin_can_hit_register():
    client = TestClient(app)
    payload = {"url": "https://example.com/hooks/test-register"}
    res = client.post(
        "/api/webhooks/register",
        json=payload,
        headers={"X-User-Role": "admin"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["url"] == payload["url"]
    assert data.get("signing_secret")
