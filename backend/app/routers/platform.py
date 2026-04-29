"""KPI stubs for onboarding / governance (Brief §4.6)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/platform", tags=["platform"])


@router.get("/kpis", response_model=schemas.KpiSummaryOut)
def kpis(db: Session = Depends(get_db)):
    pub = db.query(func.count(models.Rule.id)).filter(
        models.Rule.review_status == "published"
    ).scalar() or 0
    ev = db.query(func.count(models.OutcomeEvent.id)).scalar() or 0
    src = db.query(func.count(models.Source.id)).filter(
        models.Source.status == "processed"
    ).scalar() or 0
    return schemas.KpiSummaryOut(
        rules_published=int(pub),
        outcome_events=int(ev),
        active_sources=int(src),
    )
