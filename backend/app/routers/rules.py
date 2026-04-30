"""Rule CRUD + listing endpoints (read-side and lightweight create)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..middleware.rbac import require_role, tenant_id_dep
from ..services import review_service, validation, versioning
from ..services.backfill_service import sync_canonical_fields_for_new_rule
from ..services.cache_service import invalidate_enforcement_caches
from ..services.governance_service import publish_diagnostics

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("", response_model=list[schemas.RuleOut])
def list_rules(
    state: Optional[str] = None,
    tax_category: Optional[str] = None,
    tax_type: Optional[str] = None,
    review_status: Optional[str] = None,
    workflow_stage: Optional[str] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(tenant_id_dep),
):
    rules = review_service.list_rules(
        db,
        tenant_id=tenant_id,
        state=state,
        tax_category=tax_category or tax_type,
        review_status=review_status,
        workflow_stage=workflow_stage,
        limit=limit,
    )
    return [schemas.RuleOut.model_validate(r) for r in rules]


@router.get("/{rule_id}", response_model=schemas.RuleOut)
def get_rule(rule_id: str, db: Session = Depends(get_db), tenant_id: str = Depends(tenant_id_dep)):
    rule = review_service.get_rule(db, rule_id, tenant_id=tenant_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return schemas.RuleOut.model_validate(rule)


@router.post("", response_model=schemas.RuleOut, status_code=201)
def create_rule(
    payload: schemas.RuleCreate,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("admin")),
    tenant_id: str = Depends(tenant_id_dep),
):
    rule = models.Rule(
        tenant_id=tenant_id,
        state=payload.state,
        tax_category=payload.tax_category,
        rule_category=payload.rule_category,
        workflow_stage=payload.workflow_stage,
        operating_scenario=payload.operating_scenario,
        condition_logic=payload.condition_logic,
        submission_method=payload.submission_method,
        program_variant=payload.program_variant,
        rule_title=payload.rule_title,
        rule_summary=payload.rule_summary,
        detailed_rule=payload.detailed_rule,
        conditions=payload.conditions,
        required_actions=payload.required_actions,
        required_forms=payload.required_forms,
        required_documentation=payload.required_documentation,
        deadlines=payload.deadlines,
        exceptions=payload.exceptions,
        source_id=payload.source_id,
        source_url=payload.source_url,
        source_document_name=payload.source_document_name,
        source_snippet=payload.source_snippet,
        effective_date=payload.effective_date,
        effective_date_end=payload.effective_date_end,
        confidence_score=payload.confidence_score,
        review_status=payload.review_status,
        extraction_method=payload.extraction_method or "manual",
    )
    db.add(rule)
    db.flush()
    sync_canonical_fields_for_new_rule(db, rule)
    versioning.capture_rule_version(
        db,
        rule,
        previous_data={},
        new_data=versioning.serialize_rule(rule),
        reason="initial",
        actor="api",
    )
    db.commit()
    db.refresh(rule)
    invalidate_enforcement_caches()
    return schemas.RuleOut.model_validate(rule)


@router.get("/{rule_id}/versions", response_model=list[schemas.RuleVersionOut])
def list_rule_versions(
    rule_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(tenant_id_dep),
):
    rule = review_service.get_rule(db, rule_id, tenant_id=tenant_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    rows = (
        db.query(models.RuleVersion)
        .filter(models.RuleVersion.rule_id == rule_id)
        .order_by(models.RuleVersion.version.desc())
        .all()
    )
    return [schemas.RuleVersionOut.model_validate(r) for r in rows]


@router.post("/{rule_id}/validate", response_model=schemas.RuleAssessmentOut)
def validate_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("reviewer")),
    tenant_id: str = Depends(tenant_id_dep),
):
    """Re-run validation + dedup/conflict detection on an existing rule.

    Returns the assessment without mutating the rule. Use this from the
    Admin/Review UI to preview what would happen on publish.
    """
    rule = review_service.get_rule(db, rule_id, tenant_id=tenant_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    payload = validation._rule_to_payload(rule)
    res, conflict = validation.assess_candidate(
        db, payload, raw_confidence=rule.confidence_score, exclude_rule_id=rule.id
    )
    return schemas.RuleAssessmentOut(
        rule_id=rule.id,
        validation=schemas.ValidationOut(**res.to_dict()),
        conflicts=schemas.ConflictOut(
            duplicate_of=conflict.duplicate_of,
            conflicting_rule_ids=conflict.conflicting_rule_ids,
            notes=conflict.notes,
        ),
    )


@router.get(
    "/{rule_id}/publish-readiness",
    response_model=schemas.PublishReadinessOut,
)
def publish_readiness(
    rule_id: str,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("reviewer")),
    tenant_id: str = Depends(tenant_id_dep),
):
    rule = review_service.get_rule(db, rule_id, tenant_id=tenant_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")

    from ..config import settings
    from ..services import validation as validation_service

    strict_enabled = bool(getattr(settings, "strict_publish_checks", False))
    # Current permissive gate (strict-only blockers are not included when strict is disabled).
    ok_permissive, _blockers = validation_service.can_publish(rule)

    rep = publish_diagnostics(rule)
    can_publish = ok_permissive if not strict_enabled else (ok_permissive and len(rep.blockers) == 0)

    return schemas.PublishReadinessOut(
        rule_id=rule.id,
        can_publish=bool(can_publish),
        strict_mode_enabled=strict_enabled,
        blockers=[schemas.PublishDiagnosticItemOut(**b.__dict__) for b in rep.blockers],
        warnings=[schemas.PublishDiagnosticItemOut(**w.__dict__) for w in rep.warnings],
        checked_fields=dict(rep.checked_fields),
    )


@router.get("/{rule_id}/conflicts", response_model=list[schemas.RuleOut])
def list_rule_conflicts(
    rule_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(tenant_id_dep),
):
    rule = review_service.get_rule(db, rule_id, tenant_id=tenant_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    payload = validation._rule_to_payload(rule)
    conflicts = validation.find_conflicting_rules(
        db, candidate=payload, exclude_rule_id=rule.id
    )
    return [schemas.RuleOut.model_validate(r) for r in conflicts]
