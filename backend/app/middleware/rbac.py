"""Stateless role context from headers (demo / tests). Replace with real auth claims later."""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any, Callable, Iterable, Optional

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

VALID_ROLES = frozenset({"admin", "reviewer", "viewer"})

_rbac_ctx: ContextVar[Optional[dict[str, Any]]] = ContextVar("rbac_ctx", default=None)


def get_rbac_audit_context() -> Optional[dict[str, Any]]:
    """Mutable dict from request context, for audit logging."""
    return _rbac_ctx.get()


def require_role(*allowed_roles: str) -> Callable[[Request], str]:
    """FastAPI dependency: allow if current role is in *allowed_roles* or is admin.

    Response body on 403 matches the project contract:
    ``{"detail": {"error": "forbidden", "required_roles": [...], "current_role": ...}}``.
    """

    required: tuple[str, ...] = tuple(allowed_roles)
    allowed: Iterable[str] = required

    def dependency(request: Request) -> str:
        role_raw = getattr(request.state, "user_role", None)
        role = role_raw if isinstance(role_raw, str) and role_raw else "viewer"
        if role == "admin" or role in frozenset(allowed):
            return role
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "required_roles": list(required),
                "current_role": role,
            },
        )

    return dependency


class RBACMiddleware(BaseHTTPMiddleware):
    """Attach ``request.state.user_role`` / ``user_id``; mirror into a ContextVar for services."""

    async def dispatch(self, request: Request, call_next):
        # CORS preflight — no ContextVar updates; attach defaults for symmetry.
        if request.method == "OPTIONS":
            raw = (request.headers.get("x-user-role") or "").strip().lower()
            request.state.user_role = raw if raw in VALID_ROLES else "viewer"
            request.state.user_id = (
                (request.headers.get("x-user-id") or "").strip() or "demo-user"
            )
            return await call_next(request)

        raw_role = (request.headers.get("x-user-role") or "").strip().lower()
        user_role = raw_role if raw_role in VALID_ROLES else "viewer"
        uid = (request.headers.get("x-user-id") or "").strip() or "demo-user"

        request.state.user_role = user_role
        request.state.user_id = uid

        token: Optional[Token] = None
        try:
            token = _rbac_ctx.set({"user_id": uid, "user_role": user_role})
            return await call_next(request)
        finally:
            if token is not None:
                _rbac_ctx.reset(token)
