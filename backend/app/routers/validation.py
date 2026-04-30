"""Submission validation + outcome feedback API (deterministic enforcement)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..middleware.rbac import require_role, tenant_id_dep
from ..services import outcomes_service, rule_engine
from ..services.webhook_delivery_service import schedule_send_event

router = APIRouter(prefix="/api", tags=["enforcement"])


def _validation_payload_for_webhook(raw: dict[str, Any], *, tenant_id: str) -> dict[str, Any]:
    return {
        "tenant_id": tenant_id,
        "valid": raw["valid"],
        "risk_level": raw["risk_level"],
        "violations": [
            {
                "rule_id": v["rule_id"],
                "rule_title": v["rule_title"],
                "reason": v["reason"],
            }
            for v in raw.get("violations", [])
        ],
        "warnings": list(raw.get("warnings") or []),
    }


def _validation_result_to_schema(
    raw: dict,
) -> schemas.ValidateSubmissionResponse:
    violations: list[schemas.SubmissionViolationOut] = []
    for v in raw.get("violations", []):
        src = v.get("source") or {}
        violations.append(
            schemas.SubmissionViolationOut(
                rule_id=v["rule_id"],
                rule_title=v["rule_title"],
                reason=v["reason"],
                required_action=v.get("required_action") or "",
                required_documentation=list(v.get("required_documentation") or []),
                confidence=float(v.get("confidence") or 0),
                source=schemas.ViolationSourceOut(
                    source_id=src.get("source_id"),
                    source_url=src.get("source_url"),
                    snippet=src.get("snippet"),
                ),
                conditions_met=list(v.get("conditions_met") or []),
                conditions_failed=list(v.get("conditions_failed") or []),
            )
        )
    passed = [
        schemas.PassedRuleOut(**p) for p in raw.get("passed_rules", [])
    ]
    return schemas.ValidateSubmissionResponse(
        valid=raw["valid"],
        risk_level=raw["risk_level"],
        violations=violations,
        warnings=list(raw.get("warnings") or []),
        passed_rules=passed,
        explanation=raw.get("explanation") or "",
    )


def _outcome_to_schema(ev) -> schemas.OutcomeEventOut:
    return schemas.OutcomeEventOut(
        id=ev.id,
        submission_id=ev.submission_id,
        state=ev.state,
        tax_category=ev.tax_category,
        workflow_stage=ev.workflow_stage,
        rejection_code=ev.rejection_code,
        rejection_reason=ev.rejection_reason,
        normalized_root_cause=ev.normalized_root_cause,
        payload=ev.payload,
        matched_rule_ids=list(ev.matched_rule_ids or []),
        coverage_status=ev.coverage_status,
        created_at=ev.created_at,
    )


@router.post(
    "/validate-submission",
    response_model=schemas.ValidateSubmissionResponse,
)
def validate_submission_endpoint(
    body: schemas.ValidateSubmissionRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(tenant_id_dep),
):
    raw = rule_engine.validate_submission(
        db,
        tenant_id=tenant_id,
        state=body.state,
        tax_category=body.tax_category,
        workflow_stage=body.workflow_stage,
        effective_date=body.effective_date,
        program_variant=body.program_variant,
        payload=body.payload,
        debug=bool(body.debug),
    )
    from ..services import audit_service

    audit_service.log(
        db,
        action="validate_submission",
        resource_type="submission",
        resource_id=None,
        actor=getattr(request.state, "user_id", None),
        detail={
            "valid": raw["valid"],
            "risk_level": raw["risk_level"],
            "violation_count": len(raw.get("violations") or []),
            "state": body.state,
            "tax_category": body.tax_category,
            "workflow_stage": body.workflow_stage,
        },
    )
    schedule_send_event(
        background_tasks,
        "submission.validated",
        _validation_payload_for_webhook(raw, tenant_id=tenant_id),
    )
    return _validation_result_to_schema(raw)


@router.post("/outcomes", response_model=schemas.OutcomeCreateResponse)
def create_outcome_endpoint(
    body: schemas.OutcomeCreateRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("reviewer")),
    tenant_id: str = Depends(tenant_id_dep),
):
    ev, meta = outcomes_service.create_outcome(
        db,
        tenant_id=tenant_id,
        submission_id=body.submission_id,
        state=body.state,
        tax_category=body.tax_category,
        workflow_stage=body.workflow_stage,
        effective_date=body.effective_date,
        rejection_code=body.rejection_code,
        rejection_reason=body.rejection_reason,
        payload=body.payload,
    )
    snap = meta["validation_at_outcome"]
    from ..services import audit_service

    audit_service.log(
        db,
        action="outcome_created",
        resource_type="outcome",
        resource_id=ev.id,
        actor=getattr(request.state, "user_id", None),
        detail={
            "state": ev.state,
            "tax_category": ev.tax_category,
            "coverage_status": ev.coverage_status,
            "submission_id": ev.submission_id,
            "rejection_code": body.rejection_code,
            "matched_rule_count": len(ev.matched_rule_ids or []),
        },
    )
    schedule_send_event(
        background_tasks,
        "outcome.created",
        {
            "tenant_id": tenant_id,
            "outcome_id": ev.id,
            "state": ev.state,
            "tax_category": ev.tax_category,
            "workflow_stage": ev.workflow_stage,
            "coverage_status": ev.coverage_status,
            "rejection_code": ev.rejection_code,
            "rejection_reason_preview": (ev.rejection_reason or "")[:500],
            "submission_id": ev.submission_id,
        },
    )
    return schemas.OutcomeCreateResponse(
        outcome=_outcome_to_schema(ev),
        coverage_status=ev.coverage_status,
        matched_rule_ids=list(ev.matched_rule_ids or []),
        validation_at_outcome=schemas.OutcomeValidationSnapshotOut(
            valid=snap["valid"],
            risk_level=snap["risk_level"],
            violation_rule_ids=snap["violation_rule_ids"],
        ),
    )


@router.get("/outcomes", response_model=list[schemas.OutcomeEventOut])
def list_outcomes_endpoint(
    state: str | None = None,
    tax_category: str | None = None,
    coverage_status: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(tenant_id_dep),
):
    rows = outcomes_service.list_outcomes(
        db,
        tenant_id=tenant_id,
        state=state,
        tax_category=tax_category,
        coverage_status=coverage_status,
        limit=limit,
    )
    return [_outcome_to_schema(r) for r in rows]
