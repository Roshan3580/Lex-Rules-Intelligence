"""Governance catalog and publish completeness checks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy.orm import Session

from .. import models
from ..config import settings


def ensure_jurisdiction_seed(db: Session) -> int:
    """Idempotent US-state rows for jurisdiction FK (subset)."""
    samples = [
        ("US-CA", "California"),
        ("US-TX", "Texas"),
        ("US-NY", "New York"),
    ]
    added = 0
    for code, name in samples:
        q = db.query(models.Jurisdiction).filter(models.Jurisdiction.code == code).first()
        if q is None:
            db.add(models.Jurisdiction(code=code, display_name=name))
            added += 1
    if added:
        db.commit()
    return added


def ensure_rejection_reason_seed(db: Session) -> int:
    """Seed common rejection codes for mapping / analytics."""
    seeds = [
        ("MISSING_FORM", "Required form not attached", "documentation"),
        ("LATE_FILING", "Filing after deadline", "timing"),
        ("WRONG_PORTAL", "Submitted via incorrect channel", "submission"),
    ]
    added = 0
    for code, label, cat in seeds:
        if db.query(models.RejectionReason).filter(models.RejectionReason.code == code).first():
            continue
        db.add(
            models.RejectionReason(code=code, label=label, category=cat)
        )
        added += 1
    if added:
        db.commit()
    return added


def strict_publish_blockers(rule: models.Rule) -> list[str]:
    """Legacy wrapper: return message strings when strict mode is enabled."""
    if not getattr(settings, "strict_publish_checks", False):
        return []
    rep = publish_diagnostics(rule)
    return [b.message for b in rep.blockers]


@dataclass(frozen=True)
class PublishDiagnosticItem:
    code: str
    message: str
    severity: str  # "error" | "warning"


@dataclass(frozen=True)
class PublishDiagnostics:
    blockers: list[PublishDiagnosticItem]
    warnings: list[PublishDiagnosticItem]
    checked_fields: dict[str, bool]


def _has_source_reference(rule: models.Rule) -> bool:
    return bool(rule.source_id or rule.source_url or (rule.source_snippet or "").strip())


def _has_lineage(rule: models.Rule) -> bool:
    return bool(
        rule.extraction_run_id
        or (rule.lineage if isinstance(rule.lineage, dict) and len(rule.lineage) > 0 else None)
        or (rule.extractor_model_version or "").strip()
        or (rule.extractor_prompt_version or "").strip()
    )


def _condition_logic_malformed(rule: models.Rule) -> bool:
    raw = rule.condition_logic
    if raw is None:
        return False
    if isinstance(raw, str):
        t = raw.strip()
        if not t:
            return False
        try:
            json.loads(t)
            return False
        except Exception:
            return True
    if isinstance(raw, dict):
        return False
    return True


def publish_diagnostics(rule: models.Rule) -> PublishDiagnostics:
    """Always compute governance diagnostics (independent of strict mode)."""
    from .validation import MIN_PUBLISH_CONFIDENCE

    blockers: list[PublishDiagnosticItem] = []
    warnings: list[PublishDiagnosticItem] = []

    checked: dict[str, bool] = {}

    eff_ok = bool((rule.effective_date or "").strip())
    checked["effective_date"] = eff_ok
    if not eff_ok:
        blockers.append(
            PublishDiagnosticItem(
                code="missing_effective_date",
                message="Rule must have an effective date before publishing.",
                severity="error",
            )
        )

    src_ok = _has_source_reference(rule)
    checked["source_ref"] = src_ok
    if not src_ok:
        blockers.append(
            PublishDiagnosticItem(
                code="missing_source_reference",
                message="Rule must include source evidence (source_id, source_url, or source_snippet).",
                severity="error",
            )
        )

    conf_ok = rule.confidence_score is not None and float(rule.confidence_score) >= MIN_PUBLISH_CONFIDENCE
    checked["confidence"] = bool(conf_ok)
    if not checked["confidence"]:
        warnings.append(
            PublishDiagnosticItem(
                code="low_confidence",
                message=f"Confidence is below recommended threshold ({MIN_PUBLISH_CONFIDENCE:.2f}).",
                severity="warning",
            )
        )

    # Structured action check: for later phases we want explicit operator steps in the rule.
    stage = (rule.workflow_stage or "").strip().lower()
    action_required = stage in ("submission", "documentation", "intake")
    has_action = bool(
        (rule.required_actions and len(rule.required_actions) > 0)
        or (rule.required_actions_structured and len(rule.required_actions_structured) > 0)
        or (rule.required_documentation and len(rule.required_documentation) > 0)
        or (rule.required_forms and len(rule.required_forms) > 0)
    )
    checked["structured_action"] = (not action_required) or has_action
    if action_required and not has_action:
        blockers.append(
            PublishDiagnosticItem(
                code="missing_required_action",
                message="Rule should include required actions/forms/documentation for this workflow stage.",
                severity="error",
            )
        )

    lin_ok = _has_lineage(rule)
    checked["lineage"] = lin_ok
    if not lin_ok:
        blockers.append(
            PublishDiagnosticItem(
                code="missing_lineage",
                message="Rule should include lineage (extraction_run_id or lineage metadata).",
                severity="error",
            )
        )

    tenant_ok = bool((rule.tenant_id or "").strip())
    checked["tenant_id"] = tenant_ok
    if not tenant_ok:
        blockers.append(
            PublishDiagnosticItem(
                code="missing_tenant_id",
                message="Rule must have tenant_id set.",
                severity="error",
            )
        )

    if _condition_logic_malformed(rule):
        blockers.append(
            PublishDiagnosticItem(
                code="malformed_condition_logic",
                message="condition_logic is malformed JSON.",
                severity="error",
            )
        )

    # Publish flow: approved → publish unless already published.
    checked["review_status"] = bool(rule.review_status in ("approved", "published"))
    if rule.review_status not in ("approved", "published"):
        blockers.append(
            PublishDiagnosticItem(
                code="missing_approval",
                message="Rule must be approved before publishing.",
                severity="error",
            )
        )

    return PublishDiagnostics(blockers=blockers, warnings=warnings, checked_fields=checked)
