"""Append-only audit log for governance (Brief §8)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from .. import models


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
    db.add(
        models.AuditLogEntry(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor=actor,
            detail=detail,
            tenant_id=tenant_id,
        )
    )
    db.commit()
