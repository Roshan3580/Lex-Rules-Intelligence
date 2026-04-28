"""Rule CRUD + listing endpoints (read-side and lightweight create)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..services import review_service

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("", response_model=list[schemas.RuleOut])
def list_rules(
    state: Optional[str] = None,
    tax_category: Optional[str] = None,
    review_status: Optional[str] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    rules = review_service.list_rules(
        db,
        state=state,
        tax_category=tax_category,
        review_status=review_status,
        limit=limit,
    )
    return [schemas.RuleOut.model_validate(r) for r in rules]


@router.get("/{rule_id}", response_model=schemas.RuleOut)
def get_rule(rule_id: str, db: Session = Depends(get_db)):
    rule = review_service.get_rule(db, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return schemas.RuleOut.model_validate(rule)


@router.post("", response_model=schemas.RuleOut, status_code=201)
def create_rule(payload: schemas.RuleCreate, db: Session = Depends(get_db)):
    rule = models.Rule(
        state=payload.state,
        tax_category=payload.tax_category,
        rule_title=payload.rule_title,
        rule_summary=payload.rule_summary,
        detailed_rule=payload.detailed_rule,
        conditions=payload.conditions,
        required_actions=payload.required_actions,
        required_forms=payload.required_forms,
        deadlines=payload.deadlines,
        exceptions=payload.exceptions,
        source_id=payload.source_id,
        source_url=payload.source_url,
        source_document_name=payload.source_document_name,
        source_snippet=payload.source_snippet,
        effective_date=payload.effective_date,
        confidence_score=payload.confidence_score,
        review_status=payload.review_status,
        extraction_method=payload.extraction_method or "manual",
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return schemas.RuleOut.model_validate(rule)
