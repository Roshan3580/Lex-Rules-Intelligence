"""Admin read models: KPIs, taxonomy bundles, audit feed.

Phase 8 placeholder RBAC: callers pass `X-User-Role` (or actor) from the
client; real auth can replace this without changing the response shapes.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..services import validation


def _last_ingestion_run(db: Session) -> Optional[dict[str, Any]]:
    run = (
        db.query(models.IngestionRun)
        .order_by(models.IngestionRun.started_at.desc())
        .first()
    )
    if run is None:
        return None
    return {
        "id": run.id,
        "kind": run.kind,
        "status": run.status,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "total": run.total,
        "ingested": run.ingested,
        "errors": run.errors,
    }


def build_taxonomy() -> dict[str, Any]:
    """Static + canonical vocab for the Admin taxonomy panel."""
    tax_categories = list(schemas.TAX_CATEGORIES)
    workflow_stages = sorted(
        validation.VALID_WORKFLOW_STAGES | {"rejection_resolution"}
    )
    source_types = [
        "pdf",
        "url",
        "text",
        "manual",
        "upload",
        "webpage",
    ]
    return {
        "tax_categories": tax_categories,
        "workflow_stages": workflow_stages,
        "source_types": source_types,
        "review_statuses": list(schemas.REVIEW_STATUSES),
    }


def admin_summary(db: Session) -> dict[str, Any]:
    total_sources = db.query(func.count(models.Source.id)).scalar() or 0
    total_rules = db.query(func.count(models.Rule.id)).scalar() or 0
    published_rules = (
        db.query(func.count(models.Rule.id))
        .filter(models.Rule.review_status == "published")
        .scalar()
        or 0
    )
    rules_in_review = (
        db.query(func.count(models.Rule.id))
        .filter(
            models.Rule.review_status.in_(
                ["draft", "needs_review", "auto_validated"]
            )
        )
        .scalar()
        or 0
    )
    failed_sources = (
        db.query(func.count(models.Source.id))
        .filter(models.Source.status == "failed")
        .scalar()
        or 0
    )
    avg_confidence = (
        db.query(func.avg(models.Rule.confidence_score)).scalar()
    )
    if avg_confidence is None:
        avg_confidence = 0.0
    extraction_rows = (
        db.query(models.Rule.extraction_method, func.count(models.Rule.id))
        .group_by(models.Rule.extraction_method)
        .all()
    )
    extraction_breakdown: dict[str, int] = {}
    for method, cnt in extraction_rows:
        key = method or "unknown"
        extraction_breakdown[key] = int(cnt)

    return {
        "total_sources": int(total_sources),
        "total_rules": int(total_rules),
        "published_rules": int(published_rules),
        "rules_in_review": int(rules_in_review),
        "failed_sources": int(failed_sources),
        "avg_confidence": float(avg_confidence),
        "extraction_breakdown": extraction_breakdown,
        "last_ingestion_run": _last_ingestion_run(db),
    }
