"""Analytics API (Phase 10): chart-ready aggregates."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..services import analytics_service

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("", response_model=schemas.AnalyticsOut)
def get_analytics(
    days: int = 30,
    db: Session = Depends(get_db),
):
    data = analytics_service.build_analytics(db, days=days)
    return schemas.AnalyticsOut(
        rules_by_state=data["rules_by_state"],
        rules_by_tax_category=data["rules_by_tax_category"],
        confidence_distribution=data["confidence_distribution"],
        sources_by_status=data["sources_by_status"],
        extraction_methods=data["extraction_methods"],
        rules_created_by_day=data["rules_created_by_day"],
        review_events_by_day=data["review_events_by_day"],
        source_freshness=data["source_freshness"],
        window_days=data["window_days"],
        summary=schemas.AnalyticsSummaryOut(**data["summary"]),
    )
