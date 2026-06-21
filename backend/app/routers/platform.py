"""KPI stubs for onboarding / governance + cache introspection."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..middleware.rbac import require_role, tenant_id_dep
from ..services.backfill_service import canonical_consistency_report, run_backfill
from ..services.cache_service import (
    NAMESPACE_RULE_LOOKUP,
    NAMESPACE_VALIDATION,
    default_cache,
)

router = APIRouter(prefix="/api/platform", tags=["platform"])


@router.get("/kpis", response_model=schemas.KpiSummaryOut)
def kpis(db: Session = Depends(get_db), tenant_id: str = Depends(tenant_id_dep)):
    pub = db.query(func.count(models.Rule.id)).filter(
        models.Rule.tenant_id == tenant_id
    ).filter(
        models.Rule.review_status == "published"
    ).scalar() or 0
    ev = (
        db.query(func.count(models.OutcomeEvent.id))
        .filter(models.OutcomeEvent.tenant_id == tenant_id)
        .scalar()
        or 0
    )
    src = db.query(func.count(models.Source.id)).filter(
        models.Source.tenant_id == tenant_id
    ).filter(
        models.Source.status == "processed"
    ).scalar() or 0
    return schemas.KpiSummaryOut(
        rules_published=int(pub),
        outcome_events=int(ev),
        active_sources=int(src),
    )


@router.get("/cache", response_model=schemas.CacheMetricsOut)
def cache_metrics(_: str = Depends(require_role("reviewer"))):
    raw = default_cache().stats()
    return schemas.CacheMetricsOut(
        global_process_cache_stats=True,
        namespaces={
            ns: schemas.CacheNamespaceStatsOut(**stats) for ns, stats in raw.items()
        }
    )


@router.post("/cache/clear")
def cache_clear(
    _: str = Depends(require_role("admin")),
    body: schemas.CacheClearRequest = Body(
        default_factory=lambda: schemas.CacheClearRequest()
    ),
):
    svc = default_cache()
    if body.namespace:
        if body.namespace not in (NAMESPACE_RULE_LOOKUP, NAMESPACE_VALIDATION):
            raise HTTPException(
                status_code=400,
                detail=f"namespace must be {NAMESPACE_RULE_LOOKUP!r} or {NAMESPACE_VALIDATION!r}",
            )
        svc.clear_namespace(body.namespace)
    else:
        svc.clear_all()
    return {"status": "ok"}


@router.get("/canonical-report", response_model=schemas.CanonicalConsistencyReportOut)
def platform_canonical_report(
    db: Session = Depends(get_db),
    _: str = Depends(require_role("reviewer")),
    tenant_id: str = Depends(tenant_id_dep),
):
    raw = canonical_consistency_report(db, tenant_id=tenant_id)
    return schemas.CanonicalConsistencyReportOut(**raw)


@router.post("/backfill", response_model=schemas.CanonicalBackfillResponse)
def platform_backfill(
    body: schemas.CanonicalBackfillRequest,
    request: Request,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(tenant_id_dep),
):
    """Dry-run: reviewer or admin. Persist: admin only."""
    role = getattr(request.state, "user_role", None) or "viewer"
    if body.dry_run:
        if role not in ("admin", "reviewer"):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "forbidden",
                    "required_roles": ["reviewer", "admin"],
                    "current_role": role,
                },
            )
    elif role != "admin":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "required_roles": ["admin"],
                "current_role": role,
            },
        )
    changes, summary = run_backfill(
        db, target=body.target, tenant_id=tenant_id, dry_run=body.dry_run
    )
    if not body.dry_run:
        db.commit()
    return schemas.CanonicalBackfillResponse(
        dry_run=body.dry_run,
        target=body.target,
        changes=changes,
        summary=summary,
    )


@router.get("/governance-config", response_model=schemas.GovernanceConfigOut)
def governance_config(_: str = Depends(require_role("reviewer"))):
    from ..config import settings
    from ..services.validation import MIN_PUBLISH_CONFIDENCE

    return schemas.GovernanceConfigOut(
        strict_publish_checks=bool(getattr(settings, "strict_publish_checks", False)),
        min_publish_confidence=float(MIN_PUBLISH_CONFIDENCE),
    )
