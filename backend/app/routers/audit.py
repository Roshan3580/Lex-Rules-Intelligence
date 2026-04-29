"""Read-only governance audit trail (append-only entries from ``audit_service.log``)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..middleware.rbac import require_role
from ..schemas import AuditLogsResponse
from ..services import audit_service

router = APIRouter(prefix="/api", tags=["audit"])


@router.get("/audit", response_model=AuditLogsResponse)
def get_audit_logs(
    db: Session = Depends(get_db),
    _: str = Depends(require_role("reviewer")),
    entity_type: str | None = Query(
        None, description="Filter by resource / entity type (maps to ``resource_type``)"
    ),
    entity_id: str | None = Query(
        None, description="Filter by resource / entity id (maps to ``resource_id``)"
    ),
    action: str | None = Query(None),
    actor: str | None = Query(None),
    limit: int = Query(100, ge=1, le=audit_service.AUDIT_LIST_MAX_LIMIT),
    offset: int = Query(0, ge=0),
):
    rows, total = audit_service.list_audit_logs(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor=actor,
        limit=limit,
        offset=offset,
    )
    return AuditLogsResponse(
        logs=[audit_service.audit_log_public_from_row(r) for r in rows],
        total=total,
    )
