"""Review service: human-in-the-loop actions on extracted rules.

Editing/approving/rejecting/publishing all flow through here so that every
state change creates a ReviewEvent for traceability (Section 4.5 of the
brief — versioning, lineage, audit trail).
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from .. import models, schemas
from . import versioning


_VALID_ACTIONS = {"approve", "reject", "publish", "needs_review", "edit"}

_ACTION_TO_STATUS = {
    "approve": "approved",
    "reject": "rejected",
    "publish": "published",
    "needs_review": "needs_review",
}


def list_rules(
    db: Session,
    *,
    state: Optional[str] = None,
    tax_category: Optional[str] = None,
    review_status: Optional[str] = None,
    workflow_stage: Optional[str] = None,
    needs_review_only: bool = False,
    limit: int = 200,
) -> list[models.Rule]:
    q = db.query(models.Rule)
    if state:
        q = q.filter(models.Rule.state == state)
    if tax_category:
        q = q.filter(models.Rule.tax_category == tax_category)
    if review_status:
        q = q.filter(models.Rule.review_status == review_status)
    if workflow_stage:
        q = q.filter(models.Rule.workflow_stage == workflow_stage)
    if needs_review_only:
        q = q.filter(
            models.Rule.review_status.in_(["draft", "needs_review", "auto_validated"])
        )
    return q.order_by(models.Rule.created_at.desc()).limit(limit).all()


def get_rule(db: Session, rule_id: str) -> Optional[models.Rule]:
    return db.query(models.Rule).filter(models.Rule.id == rule_id).first()


def update_rule(
    db: Session,
    rule_id: str,
    payload: schemas.RuleUpdate,
    actor: Optional[str] = "admin",
) -> models.Rule:
    rule = get_rule(db, rule_id)
    if rule is None:
        raise LookupError(f"Rule {rule_id} not found")

    previous_data = versioning.serialize_rule(rule)

    diff: dict[str, Any] = {}
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        before = getattr(rule, k, None)
        if before != v:
            diff[k] = {"before": before, "after": v}
            setattr(rule, k, v)

    if diff:
        db.add(
            models.ReviewEvent(
                rule_id=rule.id,
                action="edit",
                actor=actor,
                diff=diff,
            )
        )
        versioning.capture_rule_version(
            db,
            rule,
            previous_data=previous_data,
            new_data=versioning.serialize_rule(rule),
            reason="edit",
            actor=actor,
        )

    db.commit()
    db.refresh(rule)
    return rule


def review_action(
    db: Session,
    rule_id: str,
    action: str,
    actor: Optional[str] = "admin",
    notes: Optional[str] = None,
) -> models.Rule:
    if action not in _VALID_ACTIONS:
        raise ValueError(f"Unknown review action: {action}")

    rule = get_rule(db, rule_id)
    if rule is None:
        raise LookupError(f"Rule {rule_id} not found")

    if action == "edit":
        # Edits go through update_rule. This branch exists for completeness.
        return rule

    new_status = _ACTION_TO_STATUS[action]
    before = rule.review_status
    previous_data = versioning.serialize_rule(rule)
    rule.review_status = new_status

    db.add(
        models.ReviewEvent(
            rule_id=rule.id,
            action=action,
            actor=actor,
            notes=notes,
            diff={"review_status": {"before": before, "after": new_status}},
        )
    )
    versioning.capture_rule_version(
        db,
        rule,
        previous_data=previous_data,
        new_data=versioning.serialize_rule(rule),
        reason="review_action",
        actor=actor,
        notes=f"action={action}",
    )
    db.commit()
    db.refresh(rule)
    return rule


def list_events(db: Session, rule_id: str) -> list[models.ReviewEvent]:
    return (
        db.query(models.ReviewEvent)
        .filter(models.ReviewEvent.rule_id == rule_id)
        .order_by(models.ReviewEvent.created_at.desc())
        .all()
    )


def list_all_events(
    db: Session,
    *,
    limit: int = 100,
) -> list[tuple[models.ReviewEvent, models.Rule]]:
    """Global review audit trail for Admin / dashboard (newest first)."""
    return (
        db.query(models.ReviewEvent, models.Rule)
        .join(models.Rule, models.ReviewEvent.rule_id == models.Rule.id)
        .order_by(models.ReviewEvent.created_at.desc())
        .limit(min(max(limit, 1), 500))
        .all()
    )
