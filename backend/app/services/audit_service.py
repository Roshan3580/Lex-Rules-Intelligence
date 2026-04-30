"""Append-only audit log for governance (Brief §8)."""

from __future__ import annotations

import re
from typing import Any, Optional, Sequence, Tuple

from sqlalchemy import desc
from sqlalchemy.orm import Session

from .. import models
from ..middleware.rbac import get_rbac_audit_context
from ..schemas import AuditLogPublic

# Maximum rows returned per list request (enforce in API queries).
AUDIT_LIST_MAX_LIMIT = 500

_SENSITIVE_KEY_RE = re.compile(
    r"(secret|password|passwd|token|authorization|credential|signing|api[_-]?key)",
    re.IGNORECASE,
)


def sanitize_audit_detail_for_public(detail: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Strip risky keys from persisted JSON (never expose signing secrets, etc.)."""
    if detail is None:
        return None
    out: dict[str, Any] = {}
    for k, v in detail.items():
        if _SENSITIVE_KEY_RE.search(str(k)):
            continue
        if isinstance(v, dict):
            sub = sanitize_audit_detail_for_public(v)
            if sub:
                out[k] = sub
            continue
        if isinstance(v, (list, str, int, float, bool)) or v is None:
            out[k] = v
        else:
            out[k] = str(v)[:500]
    return out or None


def audit_log_public_from_row(entry: models.AuditLogEntry) -> AuditLogPublic:
    raw_detail = dict(entry.detail) if entry.detail else {}
    ur = raw_detail.pop("user_role", None)
    sanitized = sanitize_audit_detail_for_public(raw_detail)
    return AuditLogPublic(
        id=entry.id,
        created_at=entry.created_at,
        actor=entry.actor,
        user_role=ur if isinstance(ur, str) else None,
        action=entry.action,
        entity_type=entry.resource_type,
        entity_id=entry.resource_id,
        detail=sanitized,
    )


def list_audit_logs(
    db: Session,
    *,
    tenant_id: str = "default",
    entity_type: str | None = None,
    entity_id: str | None = None,
    action: str | None = None,
    actor: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> Tuple[Sequence[models.AuditLogEntry], int]:
    """Return audit rows (newest first) and total matching count. ``limit`` is capped at 500."""
    lim = max(1, min(AUDIT_LIST_MAX_LIMIT, int(limit)))
    off = max(0, int(offset))
    q = db.query(models.AuditLogEntry).filter(models.AuditLogEntry.tenant_id == tenant_id)
    if entity_type:
        q = q.filter(models.AuditLogEntry.resource_type == entity_type)
    if entity_id:
        q = q.filter(models.AuditLogEntry.resource_id == entity_id)
    if action:
        q = q.filter(models.AuditLogEntry.action == action)
    if actor:
        q = q.filter(models.AuditLogEntry.actor == actor)
    total = q.count()
    rows = (
        q.order_by(desc(models.AuditLogEntry.created_at))
        .offset(off)
        .limit(lim)
        .all()
    )
    return rows, total


def log(
    db: Session,
    *,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    actor: Optional[str] = None,
    detail: Optional[dict[str, Any]] = None,
    tenant_id: str = "default",
) -> None:
    ctx = get_rbac_audit_context()
    if ctx and ctx.get("tenant_id") and tenant_id == "default":
        tenant_id = str(ctx.get("tenant_id") or "default")
    resolved_actor = actor
    if resolved_actor is None and ctx:
        resolved_actor = str(ctx.get("user_id") or "demo-user")
    if resolved_actor is None:
        resolved_actor = "demo-user"
    merged: Optional[dict[str, Any]]
    merged = dict(detail) if detail else {}
    if ctx and ctx.get("user_role"):
        merged.setdefault("user_role", ctx.get("user_role"))
    if not merged:
        merged = None
    db.add(
        models.AuditLogEntry(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor=resolved_actor,
            detail=merged,
            tenant_id=tenant_id,
        )
    )
    db.commit()
