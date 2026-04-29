"""Change monitoring API (Phase 11)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..services import impact_service, monitor_service
from .ingest import _item_from_db

router = APIRouter(prefix="/api/monitor", tags=["monitor"])


@router.post("/run", response_model=schemas.IngestRunResult)
def monitor_run(
    payload: schemas.MonitorRunRequest | None = None,
    db: Session = Depends(get_db),
):
    """Walk monitored sources (all, or ``source_ids``), re-fetch URLs, compare
    checksums, and re-chunk + re-extract when content changes. Sources without a
    fetchable URL only get ``last_checked`` updated. Records an ``IngestionRun``
    of kind ``monitor`` for the dashboard / Sources history panel.
    """
    payload = payload or schemas.MonitorRunRequest()
    run = monitor_service.run_monitor(
        db,
        source_ids=payload.source_ids,
        limit=payload.limit,
        auto_extract=payload.auto_extract,
    )
    items_db = (
        db.query(models.IngestionRunItem)
        .filter(models.IngestionRunItem.run_id == run.id)
        .order_by(models.IngestionRunItem.created_at.asc())
        .all()
    )
    return schemas.IngestRunResult(
        total=run.total,
        ingested=run.ingested,
        duplicates=run.duplicates,
        errors=run.errors,
        items=[_item_from_db(it) for it in items_db],
        run_id=run.id,
    )


@router.post("/impact")
def monitor_impact(source_id: str = Query(...), db: Session = Depends(get_db)):
    return impact_service.analyze_source_impact(db, source_id=source_id)
