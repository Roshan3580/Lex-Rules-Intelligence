"""Admin surface: taxonomy, KPI summary, global review audit (Phase 8)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..config import settings
from ..database import get_db
from ..services import admin_service, review_service
from ..services.embeddings import embedder
from ..services.retrieval_service import last_mode as retrieval_last_mode
from ..services.vector_store import vector_store

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/roles", response_model=list[schemas.AdminRoleOut])
def list_roles():
    """Placeholder roles until real auth + RBAC ships."""
    return [
        schemas.AdminRoleOut(
            id="admin",
            label="Admin",
            description="Full access: ingestion, publishing, taxonomy view.",
        ),
        schemas.AdminRoleOut(
            id="reviewer",
            label="Reviewer",
            description="Ingest sources and move rules through review.",
        ),
        schemas.AdminRoleOut(
            id="viewer",
            label="Viewer",
            description="View audit and stats; read-only against mutations.",
        ),
    ]


@router.get("/taxonomy", response_model=schemas.AdminTaxonomyOut)
def get_taxonomy():
    """States come from the same canonical list as /api/states."""
    from ..routers import meta as meta_router

    states = [
        schemas.StateOut(name=n, abbreviation=a) for n, a in meta_router._US_STATES
    ]
    bundle = admin_service.build_taxonomy()
    return schemas.AdminTaxonomyOut(states=states, **bundle)


@router.get("/summary", response_model=schemas.AdminSummaryOut)
def get_summary(db: Session = Depends(get_db)):
    s = admin_service.admin_summary(db)
    vstats = vector_store.stats()
    return schemas.AdminSummaryOut(
        total_sources=s["total_sources"],
        total_rules=s["total_rules"],
        published_rules=s["published_rules"],
        rules_in_review=s["rules_in_review"],
        failed_sources=s["failed_sources"],
        avg_confidence=s["avg_confidence"],
        extraction_breakdown=s["extraction_breakdown"],
        last_ingestion_run=s["last_ingestion_run"],
        llm_enabled=settings.llm_enabled,
        retrieval_mode=retrieval_last_mode(),
        embedding_provider=embedder.name,
        vector_index_size=int(vstats.get("size") or 0),
    )


@router.get("/audit", response_model=list[schemas.ReviewAuditEventOut])
def list_audit(
    limit: int = 80,
    db: Session = Depends(get_db),
):
    rows = review_service.list_all_events(db, limit=limit)
    out: list[schemas.ReviewAuditEventOut] = []
    for ev, rule in rows:
        out.append(
            schemas.ReviewAuditEventOut(
                id=ev.id,
                rule_id=ev.rule_id,
                rule_title=rule.rule_title,
                state=rule.state,
                tax_category=rule.tax_category,
                action=ev.action,
                actor=ev.actor,
                notes=ev.notes,
                diff=ev.diff,
                created_at=ev.created_at,
            )
        )
    return out
