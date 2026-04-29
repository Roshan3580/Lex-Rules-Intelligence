"""Admin review endpoints."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..services import review_service, validation

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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # Publish gate: validation + confidence + human approve (brief §8).
    if payload.action == "publish":
        existing = review_service.get_rule(db, rule_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Rule not found")
        ok, blockers = validation.can_publish(existing)
        if not ok:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Rule cannot be published",
                    "blockers": blockers,
                },
            )

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

    from ..services import audit_service

    if payload.action in ("publish", "approve", "reject", "edit"):
        audit_service.log(
            db,
            action=payload.action,
            resource_type="rule",
            resource_id=rule_id,
            actor=payload.actor,
            detail={"notes": payload.notes},
        )

    if payload.action == "publish":
        from ..services import webhook_delivery_service

        webhook_delivery_service.schedule_send_event(
            background_tasks,
            "rule.published",
            {
                "rule_id": rule.id,
                "rule_title": rule.rule_title,
                "state": rule.state,
                "tax_category": rule.tax_category,
                "review_status": rule.review_status,
            },
        )

    return schemas.RuleOut.model_validate(rule)


@router.get("/rules/{rule_id}/events", response_model=list[schemas.ReviewEventOut])
def rule_events(rule_id: str, db: Session = Depends(get_db)):
    events = review_service.list_events(db, rule_id)
    return [schemas.ReviewEventOut.model_validate(e) for e in events]
