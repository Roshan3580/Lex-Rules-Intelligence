"""Batch change monitoring — re-check sources and compare checksums (Phase 11)."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from .. import models
from . import ingestion_runs, ingestion_service


def run_monitor(
    db: Session,
    *,
    tenant_id: str = "default",
    source_ids: Optional[list[str]] = None,
    limit: int = 50,
    auto_extract: bool = True,
) -> models.IngestionRun:
    """Check sources for URL content changes; record an IngestionRun.

    With no ``source_ids`` filter, all sources in the catalog are visited up
    to ``limit`` (non-URL rows only get ``last_checked`` via
    ``skipped_no_url`` in ``refresh_monitored_source``).
    """
    cap = max(1, min(limit, 200))
    run = ingestion_runs.start_run(
        db,
        kind="monitor",
        tenant_id=tenant_id,
        triggered_by="api:/api/monitor/run",
        notes=f"limit={cap} auto_extract={auto_extract}",
    )

    q = db.query(models.Source).filter(models.Source.tenant_id == tenant_id)
    if source_ids:
        q = q.filter(models.Source.id.in_(source_ids))
    # When no filter: every source is visited — URL-backed rows are
    # re-fetched; paste/upload/manual rows only get ``last_checked`` bumped
    # inside ``refresh_monitored_source``.
    sources = q.order_by(models.Source.updated_at.asc()).limit(cap).all()

    for src in sources:
        sid = src.id
        res = ingestion_service.refresh_monitored_source(
            db, src, auto_extract=auto_extract
        )
        fresh = db.get(models.Source, sid)
        if fresh is None:
            continue
        outcome = res.get("outcome", "failed")

        if outcome == "unchanged":
            ingestion_runs.record_item(
                db,
                run,
                tenant_id=tenant_id,
                source=fresh,
                status="unchanged",
                chunks_created=0,
                rules_created=0,
            )
        elif outcome == "updated":
            ingestion_runs.record_item(
                db,
                run,
                tenant_id=tenant_id,
                source=fresh,
                status="updated",
                chunks_created=int(res.get("chunks") or 0),
                rules_created=int(res.get("rules") or 0),
                extraction_method=res.get("extraction_method"),
            )
        elif outcome == "skipped_no_url":
            ingestion_runs.record_item(
                db,
                run,
                tenant_id=tenant_id,
                source=fresh,
                status="skipped",
                chunks_created=0,
                rules_created=0,
            )
        else:
            ingestion_runs.record_item(
                db,
                run,
                tenant_id=tenant_id,
                source=fresh,
                status="failed",
                chunks_created=0,
                rules_created=0,
                error_message=res.get("error") or "monitor failed",
            )

    return ingestion_runs.finish_run(db, run)
