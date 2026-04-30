"""Dashboard overview: KPIs, activity feed, change alerts (Phase 9)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..config import settings
from ..database import get_db
from ..middleware.rbac import tenant_id_dep
from ..services import admin_service, dashboard_service
from ..services.embeddings import embedder
from ..services.retrieval_service import last_mode as retrieval_last_mode
from ..services.vector_store import vector_store

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=schemas.DashboardOut)
def get_dashboard(
    activity_limit: int = 40,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(tenant_id_dep),
):
    summary = admin_service.admin_summary(db, tenant_id=tenant_id)
    vstats = vector_store.stats()
    kpis = schemas.DashboardKPIsOut(
        total_sources=summary["total_sources"],
        total_rules=summary["total_rules"],
        published_rules=summary["published_rules"],
        rules_in_review=summary["rules_in_review"],
        avg_confidence=summary["avg_confidence"],
        failed_sources=summary["failed_sources"],
        last_ingestion_run=summary["last_ingestion_run"],
        llm_enabled=settings.llm_enabled,
        retrieval_mode=retrieval_last_mode(),
        embedding_provider=embedder.name,
        vector_index_size=int(vstats.get("size") or 0),
    )
    activities_raw = dashboard_service.build_activities(
        db, tenant_id=tenant_id, limit=activity_limit
    )
    alerts_raw = dashboard_service.build_alerts(
        db, tenant_id=tenant_id, summary=summary
    )
    activities = [schemas.DashboardActivityOut(**a) for a in activities_raw]
    alerts = [schemas.DashboardAlertOut(**a) for a in alerts_raw]
    return schemas.DashboardOut(kpis=kpis, activities=activities, alerts=alerts)
