"""Stateful workflow execution gated by deterministic rule_engine."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from .. import models
from . import rule_engine, workflows_service


def resolve_case(db: Session, case_id_or_pk: str) -> Optional[models.CaseWorkflow]:
    c = db.get(models.CaseWorkflow, case_id_or_pk)
    if c is None:
        c = (
            db.query(models.CaseWorkflow)
            .filter(models.CaseWorkflow.case_id == case_id_or_pk)
            .first()
        )
    return c


def run_start(
    db: Session,
    *,
    tenant_id: str = "default",
    state: Optional[str],
    tax_category: Optional[str],
    title: Optional[str] = None,
    org: Optional[str] = None,
    template_id: Optional[str] = None,
    case_id: Optional[str] = None,
    actor: Optional[str] = None,
    validation_payload: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Create a case and attach an initial validation payload for advance checks."""
    data = workflows_service.create_case(
        db,
        tenant_id=tenant_id,
        state=state,
        tax_category=tax_category,
        title=title,
        org=org,
        template_id=template_id,
        case_id=case_id,
        actor=actor,
    )
    case = resolve_case(db, data["case_id"])
    if case is None:
        return data
    case.validation_payload = validation_payload or {
        "documents": [],
        "amount": 0,
    }
    db.add(case)
    db.commit()
    db.refresh(case)
    return workflows_service.get_case(db, case.case_id) or data


def advance(
    db: Session,
    case_id_or_pk: str,
    *,
    tenant_id: str = "default",
    validation_payload: Optional[dict[str, Any]] = None,
    actor: Optional[str] = None,
) -> dict[str, Any]:
    """Complete the current stage only if rule_engine clears the payload."""
    case = resolve_case(db, case_id_or_pk)
    if case is None:
        raise ValueError("case not found")

    merged = {**(case.validation_payload or {}), **(validation_payload or {})}
    st = rule_engine.normalize_state(case.state or "")
    stage = case.current_stage or "intake"
    val = rule_engine.validate_submission(
        db,
        tenant_id=tenant_id,
        state=st,
        tax_category=case.tax_category or "general_tax",
        workflow_stage=stage,
        effective_date=None,
        payload=merged,
    )
    if not val.get("valid"):
        return {
            "blocked": True,
            "case": workflows_service.get_case(db, case.case_id),
            "validation": val,
        }

    case.validation_payload = merged
    db.add(case)
    db.commit()

    sk = case.current_stage
    if not sk:
        return {
            "blocked": False,
            "case": workflows_service.get_case(db, case.case_id),
            "validation": val,
        }

    out = workflows_service.update_step(
        db,
        case.case_id,
        sk,
        completed=True,
        actor=actor,
    )
    return {
        "blocked": False,
        "case": out,
        "validation": val,
    }
