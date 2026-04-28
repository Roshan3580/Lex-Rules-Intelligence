"""Admin review endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..services import review_service

router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("/queue", response_model=list[schemas.RuleOut])
def review_queue(db: Session = Depends(get_db)):
    rules = review_service.list_rules(db, needs_review_only=True, limit=500)
    return [schemas.RuleOut.model_validate(r) for r in rules]


@router.patch("/rules/{rule_id}", response_model=schemas.RuleOut)
def edit_rule(
    rule_id: str,
    payload: schemas.RuleUpdate,
    db: Session = Depends(get_db),
):
    try:
        rule = review_service.update_rule(db, rule_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return schemas.RuleOut.model_validate(rule)


@router.post("/rules/{rule_id}/action", response_model=schemas.RuleOut)
def rule_action(
    rule_id: str,
    payload: schemas.ReviewActionRequest,
    db: Session = Depends(get_db),
):
    try:
        rule = review_service.review_action(
            db,
            rule_id,
            action=payload.action,
            actor=payload.actor,
            notes=payload.notes,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return schemas.RuleOut.model_validate(rule)


@router.get("/rules/{rule_id}/events", response_model=list[schemas.ReviewEventOut])
def rule_events(rule_id: str, db: Session = Depends(get_db)):
    events = review_service.list_events(db, rule_id)
    return [schemas.ReviewEventOut.model_validate(e) for e in events]
