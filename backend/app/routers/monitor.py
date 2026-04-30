"""Change monitoring API (Phase 11)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..middleware.rbac import require_role, tenant_id_dep
from ..services import impact_service, monitor_service
from ..services.cache_service import invalidate_enforcement_caches
from .ingest import _item_from_db

router = APIRouter(prefix="/api/monitor", tags=["monitor"])


@router.post("/run", response_model=schemas.IngestRunResult)
def monitor_run(
    request: Request,
    payload: schemas.MonitorRunRequest | None = None,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("reviewer")),
    tenant_id: str = Depends(tenant_id_dep),
):
    """Walk monitored sources (all, or ``source_ids``), re-fetch URLs, compare
    checksums, and re-chunk + re-extract when content changes. Sources without a
    fetchable URL only get ``last_checked`` updated. Records an ``IngestionRun``
    of kind ``monitor`` for the dashboard / Sources history panel.
    """
    payload = payload or schemas.MonitorRunRequest()
    run = monitor_service.run_monitor(
        db,
        tenant_id=tenant_id,
        source_ids=payload.source_ids,
        limit=payload.limit,
        auto_extract=payload.auto_extract,
    )
    items_db = (
        db.query(models.IngestionRunItem)
        .filter(models.IngestionRunItem.run_id == run.id)
        .filter(models.IngestionRunItem.tenant_id == tenant_id)
        .order_by(models.IngestionRunItem.created_at.asc())
        .all()
    )
    from ..services import audit_service

    audit_service.log(
        db,
        action="monitor_run",
        resource_type="monitor_run",
        resource_id=run.id,
        actor=getattr(request.state, "user_id", None),
        detail={
            "ingestion_run_kind": run.kind,
            "total": run.total,
            "ingested": run.ingested,
            "errors": run.errors,
        },
    )
    invalidate_enforcement_caches()
    return schemas.IngestRunResult(
        total=run.total,
        ingested=run.ingested,
        duplicates=run.duplicates,
        errors=run.errors,
        items=[_item_from_db(it) for it in items_db],
        run_id=run.id,
    )


@router.post("/impact")
def monitor_impact(
    source_id: str = Query(...),
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("reviewer")),
    tenant_id: str = Depends(tenant_id_dep),
):
    src = (
        db.query(models.Source)
        .filter(models.Source.tenant_id == tenant_id)
        .filter(models.Source.id == source_id)
        .first()
    )
    if src is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return impact_service.analyze_source_impact(db, source_id=source_id)
