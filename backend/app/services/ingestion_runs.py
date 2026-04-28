"""Helpers for recording ingestion history.

Every code path that ingests a source — single-URL endpoint, YAML batch,
upload, future scheduled monitor — wraps its work in an `IngestionRun`
with one `IngestionRunItem` per source attempted. This gives us a cheap
audit trail and powers `GET /api/ingest/runs`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from .. import models


def start_run(
    db: Session,
    *,
    kind: str,
    only_state: Optional[str] = None,
    only_tax_type: Optional[str] = None,
    triggered_by: Optional[str] = None,
    notes: Optional[str] = None,
) -> models.IngestionRun:
    run = models.IngestionRun(
        kind=kind,
        status="running",
        only_state=only_state,
        only_tax_type=only_tax_type,
        triggered_by=triggered_by,
        notes=notes,
        total=0,
        ingested=0,
        duplicates=0,
        errors=0,
    )
    db.add(run)
    db.flush()
    return run


def record_item(
    db: Session,
    run: models.IngestionRun,
    *,
    source: Optional[models.Source] = None,
    name: Optional[str] = None,
    url: Optional[str] = None,
    state: Optional[str] = None,
    tax_category: Optional[str] = None,
    source_type: Optional[str] = None,
    status: str,
    chunks_created: int = 0,
    rules_created: int = 0,
    extraction_method: Optional[str] = None,
    error_message: Optional[str] = None,
) -> models.IngestionRunItem:
    item = models.IngestionRunItem(
        run_id=run.id,
        source_id=source.id if source is not None else None,
        name=name or (source.name if source is not None else None),
        url=url or (source.url if source is not None else None),
        state=state or (source.state if source is not None else None),
        tax_category=tax_category
        or (source.tax_category if source is not None else None),
        source_type=source_type
        or (source.source_type if source is not None else None),
        status=status,
        chunks_created=chunks_created,
        rules_created=rules_created,
        extraction_method=extraction_method,
        error_message=(error_message or "")[:2000] or None,
    )
    db.add(item)

    run.total += 1
    if status == "ingested" or status == "updated":
        run.ingested += 1
    elif status == "duplicate":
        run.duplicates += 1
    elif status == "failed":
        run.errors += 1
    db.flush()
    return item


def finish_run(
    db: Session,
    run: models.IngestionRun,
    *,
    status: Optional[str] = None,
) -> models.IngestionRun:
    run.finished_at = datetime.utcnow()
    if status:
        run.status = status
    elif run.errors > 0 and run.ingested == 0 and run.duplicates == 0:
        run.status = "failed"
    else:
        run.status = "completed"
    db.commit()
    db.refresh(run)
    return run
