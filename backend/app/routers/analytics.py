"""Analytics API (Phase 10): chart-ready aggregates."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..middleware.rbac import tenant_id_dep
from ..services import analytics_service, outcomes_service

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("", response_model=schemas.AnalyticsOut)
def get_analytics(
    days: int = 30,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(tenant_id_dep),
):
    data = analytics_service.build_analytics(db, tenant_id=tenant_id, days=days)
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


@router.get("/rejection-coverage", response_model=schemas.RejectionCoverageOut)
def rejection_coverage(db: Session = Depends(get_db), tenant_id: str = Depends(tenant_id_dep)):
    data = outcomes_service.rejection_coverage_summary(db, tenant_id=tenant_id)
    return schemas.RejectionCoverageOut(
        total_outcomes=data["total_outcomes"],
        by_coverage_status=[
            schemas.RejectionCoverageRow(**row)
            for row in data["by_coverage_status"]
        ],
        top_rejection_reasons=[
            schemas.RejectionReasonCount(**row)
            for row in data["top_rejection_reasons"]
        ],
        missing_rule_clusters=[
            schemas.MissingRuleCluster(**row)
            for row in data["missing_rule_clusters"]
        ],
        coverage_percentage=data["coverage_percentage"],
    )


@router.get("/rejection-patterns", response_model=schemas.RejectionPatternsOut)
def rejection_patterns(db: Session = Depends(get_db), tenant_id: str = Depends(tenant_id_dep)):
    raw = outcomes_service.rejection_patterns_analysis(db, tenant_id=tenant_id)
    rows = [schemas.RejectionPatternRow(**r) for r in raw["by_state"]]
    return schemas.RejectionPatternsOut(
        by_state=rows,
        by_tax_category=rows,
        by_coverage=rows,
        rule_coverage_report=raw["rule_coverage_report"],
    )
