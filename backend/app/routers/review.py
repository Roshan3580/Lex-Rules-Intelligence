"""Admin review endpoints."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..middleware.rbac import require_role, tenant_id_dep
from ..services import review_service, validation
from ..services.cache_service import invalidate_enforcement_caches

router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("/queue", response_model=list[schemas.RuleOut])
def review_queue(db: Session = Depends(get_db), tenant_id: str = Depends(tenant_id_dep)):
    rules = review_service.list_rules(
        db, tenant_id=tenant_id, needs_review_only=True, limit=500
    )
    return [schemas.RuleOut.model_validate(r) for r in rules]


@router.patch("/rules/{rule_id}", response_model=schemas.RuleOut)
def edit_rule(
    rule_id: str,
    payload: schemas.RuleUpdate,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("reviewer")),
    tenant_id: str = Depends(tenant_id_dep),
):
    try:
        rule = review_service.update_rule(db, rule_id, payload, tenant_id=tenant_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    invalidate_enforcement_caches()
    return schemas.RuleOut.model_validate(rule)


@router.post("/rules/{rule_id}/action", response_model=schemas.RuleOut)
def rule_action(
    rule_id: str,
    payload: schemas.ReviewActionRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("reviewer")),
    tenant_id: str = Depends(tenant_id_dep),
):
    # Publish gate: validation + confidence + human approval required.
    if payload.action == "publish":
        existing = review_service.get_rule(db, rule_id, tenant_id=tenant_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Rule not found")
        ok, blockers = validation.can_publish(existing)
        if not ok:
            from ..config import settings
            from ..services.governance_service import publish_diagnostics

            rep = publish_diagnostics(existing)
            if getattr(settings, "strict_publish_checks", False):
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "publish_blocked",
                        "blockers": [b.__dict__ for b in rep.blockers],
                        "warnings": [w.__dict__ for w in rep.warnings],
                    },
                )
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
            tenant_id=tenant_id,
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
            actor=payload.actor or getattr(request.state, "user_id", None),
            detail={"notes": payload.notes},
        )

    if payload.action == "publish":
        from ..services import webhook_delivery_service

        webhook_delivery_service.schedule_send_event(
            background_tasks,
            "rule.published",
            {
                "tenant_id": tenant_id,
                "rule_id": rule.id,
                "rule_title": rule.rule_title,
                "state": rule.state,
                "tax_category": rule.tax_category,
                "review_status": rule.review_status,
            },
        )

    invalidate_enforcement_caches()
    return schemas.RuleOut.model_validate(rule)


@router.get("/rules/{rule_id}/events", response_model=list[schemas.ReviewEventOut])
def rule_events(
    rule_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(tenant_id_dep),
):
    events = review_service.list_events(db, rule_id, tenant_id=tenant_id)
    return [schemas.ReviewEventOut.model_validate(e) for e in events]
