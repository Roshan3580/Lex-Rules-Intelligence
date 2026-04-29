"""Workflow guidance service (Phase 7).

Implements the workflow layer described in the brief:

- Reusable `WorkflowTemplate`s (built-in defaults seeded once per process).
- Per-case `CaseWorkflow` instances that snapshot the template at creation
  time and progress step-by-step with an append-only audit trail.
- Live attachment of currently-published source-backed rules to each
  stage so checklists are derived from the indexed rule corpus, not from
  hard-coded mock data.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

import copy

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from .. import models

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Canonical stages used by the brief
# ---------------------------------------------------------------------------

CANONICAL_STAGES: list[dict[str, str]] = [
    {
        "key": "intake",
        "title": "Intake",
        "description": "Identify the obligation. Confirm the state, tax category, and that the activity creates a filing requirement.",
        "workflow_stage": "intake",
    },
    {
        "key": "verification",
        "title": "Verification",
        "description": "Verify nexus, registration status, thresholds, and any state-specific qualifying conditions before proceeding.",
        "workflow_stage": "verification",
    },
    {
        "key": "documentation",
        "title": "Documentation",
        "description": "Collect every form, schedule, and supporting document required by the rule.",
        "workflow_stage": "documentation",
    },
    {
        "key": "submission",
        "title": "Submission",
        "description": "File on the correct method (online portal, paper, EFT) and capture the confirmation receipt.",
        "workflow_stage": "submission",
    },
    {
        "key": "rejection_resolution",
        "title": "Rejection / Resolution",
        "description": "If a return is rejected or amended, follow the state's resolution path and document the outcome.",
        "workflow_stage": "rejection_resolution",
    },
]


_DEFAULT_CHECKLISTS: dict[str, list[dict[str, str]]] = {
    "intake": [
        {"key": "confirm_state", "label": "Confirm the state and tax category"},
        {"key": "register", "label": "Confirm registration / permit is active"},
        {"key": "filing_freq", "label": "Confirm filing frequency for this period"},
    ],
    "verification": [
        {"key": "nexus", "label": "Confirm nexus / activity threshold met"},
        {"key": "rate", "label": "Confirm applicable rate(s) for the period"},
        {"key": "exemptions", "label": "Identify any exemptions or exclusions"},
    ],
    "documentation": [
        {"key": "forms", "label": "Gather all required forms"},
        {"key": "schedules", "label": "Prepare required schedules / attachments"},
        {"key": "supporting", "label": "Attach supporting documentation"},
    ],
    "submission": [
        {"key": "method", "label": "Use the required submission method"},
        {"key": "remit", "label": "Remit any payment due by the deadline"},
        {"key": "confirm", "label": "Save the confirmation / receipt"},
    ],
    "rejection_resolution": [
        {"key": "review_reason", "label": "Review the rejection or notice reason"},
        {"key": "amend", "label": "Amend the return if required"},
        {"key": "resubmit", "label": "Resubmit and capture the new confirmation"},
    ],
}


# ---------------------------------------------------------------------------
# Default-template seeding
# ---------------------------------------------------------------------------


def _build_default_steps() -> list[dict[str, Any]]:
    """Return a fresh copy of the canonical stage list with default
    checklists attached. Snapshotted into each case at creation."""
    out: list[dict[str, Any]] = []
    for stage in CANONICAL_STAGES:
        out.append(
            {
                **stage,
                "checklist": [dict(item) for item in _DEFAULT_CHECKLISTS.get(stage["key"], [])],
            }
        )
    return out


def ensure_default_templates(db: Session) -> int:
    """Idempotently insert the default 'state-tax-filing' workflow.

    Returns the number of templates inserted (0 on subsequent calls).
    """
    existing = db.execute(
        select(models.WorkflowTemplate).where(models.WorkflowTemplate.is_builtin == True)  # noqa: E712
    ).scalars().all()
    if existing:
        return 0

    tpl = models.WorkflowTemplate(
        key="state-tax-filing",
        title="State tax filing workflow",
        description=(
            "Generic guided workflow for filing a US state tax return: "
            "intake, verification, documentation, submission, and "
            "rejection / resolution."
        ),
        state=None,
        tax_category=None,
        workflow_stage=None,
        steps=_build_default_steps(),
        required_rule_filters=[
            {"workflow_stage": s["key"]} for s in CANONICAL_STAGES
        ],
        is_builtin=True,
    )
    db.add(tpl)
    db.commit()
    logger.info("Seeded default workflow template '%s'", tpl.key)
    return 1


# ---------------------------------------------------------------------------
# Rule attachment
# ---------------------------------------------------------------------------


def _resolve_rules_for_stage(
    db: Session,
    *,
    state: Optional[str],
    tax_category: Optional[str],
    workflow_stage: Optional[str],
) -> list[models.Rule]:
    """Return published-or-approved rules that match the stage filters.

    Falls back to the broader (state, tax_category) match if no rule
    declares this exact `workflow_stage`. Always limited to a small page
    so the response payload stays light.
    """
    base = select(models.Rule).where(
        models.Rule.review_status.in_(("published", "approved", "auto_validated"))
    )
    if state:
        base = base.where(models.Rule.state == state)
    if tax_category:
        base = base.where(models.Rule.tax_category == tax_category)

    if workflow_stage:
        scoped = base.where(models.Rule.workflow_stage == workflow_stage)
        rules = list(db.execute(scoped.limit(8)).scalars().all())
        if rules:
            return rules
    return list(db.execute(base.limit(6)).scalars().all())


def _rule_summary_payload(rule: models.Rule) -> dict[str, Any]:
    return {
        "id": rule.id,
        "rule_title": rule.rule_title,
        "rule_summary": rule.rule_summary,
        "tax_category": rule.tax_category,
        "state": rule.state,
        "workflow_stage": rule.workflow_stage,
        "required_forms": rule.required_forms or [],
        "required_documentation": rule.required_documentation or [],
        "deadlines": rule.deadlines or [],
        "exceptions": rule.exceptions or [],
        "submission_method": rule.submission_method,
        "source_url": rule.source_url,
        "confidence_score": rule.confidence_score,
        "review_status": rule.review_status,
    }


def attach_rules_to_steps(
    db: Session,
    steps: list[dict[str, Any]],
    *,
    state: Optional[str],
    tax_category: Optional[str],
) -> list[dict[str, Any]]:
    """Augment a list of step dicts with `rules` populated from the live
    rule index."""
    out: list[dict[str, Any]] = []
    for step in steps:
        stage_rules = _resolve_rules_for_stage(
            db,
            state=state,
            tax_category=tax_category,
            workflow_stage=step.get("workflow_stage") or step.get("key"),
        )
        # Aggregate document/form/deadline hints from the matched rules.
        forms: set[str] = set()
        docs: set[str] = set()
        deadlines: set[str] = set()
        validations: set[str] = set()
        for r in stage_rules:
            for f in r.required_forms or []:
                forms.add(f)
            for d in r.required_documentation or []:
                docs.add(d)
            for d in r.deadlines or []:
                deadlines.add(d)
            for c in r.conditions or []:
                validations.add(c)

        out.append(
            {
                **step,
                "rules": [_rule_summary_payload(r) for r in stage_rules],
                "rule_count": len(stage_rules),
                "aggregated_forms": sorted(forms),
                "aggregated_documents": sorted(docs),
                "aggregated_deadlines": sorted(deadlines),
                "aggregated_validations": sorted(validations),
            }
        )
    return out


# ---------------------------------------------------------------------------
# Template / case CRUD
# ---------------------------------------------------------------------------


def list_templates(
    db: Session,
    *,
    state: Optional[str] = None,
    tax_category: Optional[str] = None,
    attach_rules: bool = True,
) -> list[dict[str, Any]]:
    """Return all templates, optionally with live rule attachment."""
    ensure_default_templates(db)
    stmt = select(models.WorkflowTemplate).order_by(models.WorkflowTemplate.created_at.asc())
    rows = db.execute(stmt).scalars().all()
    out: list[dict[str, Any]] = []
    for tpl in rows:
        steps = list(tpl.steps or [])
        if attach_rules:
            steps = attach_rules_to_steps(
                db, steps, state=state, tax_category=tax_category
            )
        out.append(_template_payload(tpl, steps))
    return out


def get_template(
    db: Session,
    template_id: str,
    *,
    state: Optional[str] = None,
    tax_category: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    tpl = db.get(models.WorkflowTemplate, template_id)
    if not tpl:
        return None
    steps = attach_rules_to_steps(
        db, list(tpl.steps or []), state=state, tax_category=tax_category
    )
    return _template_payload(tpl, steps)


def _template_payload(tpl: models.WorkflowTemplate, steps: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": tpl.id,
        "key": tpl.key,
        "title": tpl.title,
        "description": tpl.description,
        "state": tpl.state,
        "tax_category": tpl.tax_category,
        "workflow_stage": tpl.workflow_stage,
        "is_builtin": tpl.is_builtin,
        "steps": steps,
        "required_rule_filters": tpl.required_rule_filters or [],
        "created_at": tpl.created_at,
        "updated_at": tpl.updated_at,
    }


def create_case(
    db: Session,
    *,
    state: Optional[str],
    tax_category: Optional[str],
    title: Optional[str] = None,
    org: Optional[str] = None,
    template_id: Optional[str] = None,
    case_id: Optional[str] = None,
    actor: Optional[str] = None,
) -> dict[str, Any]:
    ensure_default_templates(db)

    tpl: Optional[models.WorkflowTemplate]
    if template_id:
        tpl = db.get(models.WorkflowTemplate, template_id)
        if tpl is None:
            raise ValueError(f"Workflow template {template_id} not found")
    else:
        tpl = db.execute(
            select(models.WorkflowTemplate).where(models.WorkflowTemplate.is_builtin == True)  # noqa: E712
        ).scalars().first()
        if tpl is None:
            ensure_default_templates(db)
            tpl = db.execute(
                select(models.WorkflowTemplate).where(models.WorkflowTemplate.is_builtin == True)  # noqa: E712
            ).scalars().first()

    snapshot = attach_rules_to_steps(
        db, list(tpl.steps or []) if tpl else _build_default_steps(),
        state=state, tax_category=tax_category,
    )
    runtime_steps = [_init_step_runtime(s) for s in snapshot]

    case = models.CaseWorkflow(
        case_id=case_id or _new_case_id(),
        org=org,
        title=title or _default_case_title(state, tax_category),
        template_id=tpl.id if tpl else None,
        state=state,
        tax_category=tax_category,
        current_stage=runtime_steps[0]["key"] if runtime_steps else None,
        status="active",
        steps=runtime_steps,
        completed_steps=[],
    )
    db.add(case)
    db.flush()

    db.add(
        models.CaseWorkflowEvent(
            case_workflow_id=case.id,
            action="case_created",
            actor=actor,
            payload={
                "template_id": tpl.id if tpl else None,
                "state": state,
                "tax_category": tax_category,
                "step_count": len(runtime_steps),
            },
        )
    )
    db.commit()
    db.refresh(case)
    return _case_payload(case)


def get_case(db: Session, case_id: str) -> Optional[dict[str, Any]]:
    """Look up by either internal id or `case_id` business key."""
    case = db.get(models.CaseWorkflow, case_id)
    if case is None:
        case = db.execute(
            select(models.CaseWorkflow).where(models.CaseWorkflow.case_id == case_id)
        ).scalars().first()
    if case is None:
        return None
    return _case_payload(case)


def list_cases(
    db: Session,
    *,
    state: Optional[str] = None,
    tax_category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    stmt = select(models.CaseWorkflow).order_by(models.CaseWorkflow.created_at.desc())
    if state:
        stmt = stmt.where(models.CaseWorkflow.state == state)
    if tax_category:
        stmt = stmt.where(models.CaseWorkflow.tax_category == tax_category)
    if status:
        stmt = stmt.where(models.CaseWorkflow.status == status)
    rows = db.execute(stmt.limit(limit)).scalars().all()
    return [_case_payload(c, include_events=False) for c in rows]


def update_step(
    db: Session,
    case_pk_or_business_id: str,
    step_key: str,
    *,
    completed: Optional[bool] = None,
    notes: Optional[str] = None,
    actor: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    case = db.get(models.CaseWorkflow, case_pk_or_business_id)
    if case is None:
        case = db.execute(
            select(models.CaseWorkflow).where(
                models.CaseWorkflow.case_id == case_pk_or_business_id
            )
        ).scalars().first()
    if case is None:
        return None

    steps = copy.deepcopy(list(case.steps or []))
    found = False
    payload_summary: dict[str, Any] = {"step_key": step_key}
    for step in steps:
        if step.get("key") != step_key:
            continue
        found = True
        if completed is True:
            step["status"] = "complete"
            step["completed_at"] = datetime.utcnow().isoformat()
        elif completed is False:
            step["status"] = "pending"
            step.pop("completed_at", None)
        if notes is not None:
            step["notes"] = notes
        payload_summary.update(step)
        break

    if not found:
        raise ValueError(f"Step '{step_key}' not found on case")

    completed_keys = [s["key"] for s in steps if s.get("status") == "complete"]
    case.steps = steps
    case.completed_steps = completed_keys
    flag_modified(case, "steps")
    flag_modified(case, "completed_steps")

    next_pending = next((s["key"] for s in steps if s.get("status") != "complete"), None)
    if next_pending is None:
        case.status = "completed"
        case.current_stage = steps[-1]["key"] if steps else None
        case.completed_at = datetime.utcnow()
    else:
        case.status = "active"
        case.current_stage = next_pending
        case.completed_at = None

    action = "complete_step" if completed else ("uncomplete_step" if completed is False else "note_step")
    db.add(
        models.CaseWorkflowEvent(
            case_workflow_id=case.id,
            action=action,
            step_key=step_key,
            actor=actor,
            notes=notes,
            payload=payload_summary,
        )
    )
    db.commit()
    db.refresh(case)
    return _case_payload(case)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _init_step_runtime(step: dict[str, Any]) -> dict[str, Any]:
    return {
        **step,
        "status": "pending",
        "completed_at": None,
        "notes": None,
        "checklist": [
            {**item, "checked": False} for item in (step.get("checklist") or [])
        ],
    }


def _default_case_title(state: Optional[str], tax_category: Optional[str]) -> str:
    parts = []
    if state:
        parts.append(state)
    if tax_category:
        parts.append(tax_category.replace("_", " "))
    if not parts:
        return "Filing case"
    return f"{' / '.join(parts)} filing case"


def _new_case_id() -> str:
    return f"CASE-{datetime.utcnow().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"


def _case_payload(case: models.CaseWorkflow, include_events: bool = True) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": case.id,
        "case_id": case.case_id,
        "title": case.title,
        "org": case.org,
        "template_id": case.template_id,
        "state": case.state,
        "tax_category": case.tax_category,
        "current_stage": case.current_stage,
        "status": case.status,
        "steps": case.steps or [],
        "completed_steps": case.completed_steps or [],
        "step_count": len(case.steps or []),
        "completed_count": len(case.completed_steps or []),
        "progress": (
            len(case.completed_steps or []) / max(1, len(case.steps or []))
            if case.steps else 0.0
        ),
        "created_at": case.created_at,
        "updated_at": case.updated_at,
        "completed_at": case.completed_at,
        "validation_payload": case.validation_payload,
    }
    if include_events:
        payload["events"] = [
            {
                "id": e.id,
                "action": e.action,
                "step_key": e.step_key,
                "actor": e.actor,
                "notes": e.notes,
                "payload": e.payload,
                "created_at": e.created_at,
            }
            for e in case.events
        ]
    return payload
