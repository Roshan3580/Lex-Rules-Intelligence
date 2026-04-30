"""Rule validation, dedup/conflict detection, and confidence policy.

Phase 4 of the upgrade plan. Three responsibilities:

1. **Schema/required-field validation** — every persisted rule must carry
   the canonical field set and have at least minimal source evidence.
2. **Duplicate + conflict detection** — same (state, tax_category,
   normalized title) is a duplicate; same key with mismatched
   forms/deadlines/required_actions is a conflict to surface in review.
3. **Confidence policy** — converts a raw extractor confidence into a
   review_status, modulated by validation results and source evidence.

All helpers are pure functions of their inputs (plus an SQLAlchemy session
for lookups). They never mutate the rule directly so callers — extraction,
review, manual create — can decide what to do with the verdict.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from sqlalchemy.orm import Session

from .. import models

# ---------------------------------------------------------------------------
# Canonical vocab
# ---------------------------------------------------------------------------

VALID_TAX_CATEGORIES: set[str] = {
    "general_tax",
    "sales_tax",
    "payroll_tax",
    "corporate_tax",
    "income_tax",
    "withholding",
    "franchise_tax",
    "other",
}

VALID_WORKFLOW_STAGES: set[str] = {
    "intake",
    "verification",
    "documentation",
    "submission",
    "resolution",
    "other",
}

VALID_SUBMISSION_METHODS: set[str] = {
    "online_portal",
    "mail",
    "in_person",
    "eft",
    "phone",
    "other",
}

VALID_REVIEW_STATUSES: set[str] = {
    "draft",
    "auto_validated",
    "needs_review",
    "approved",
    "published",
    "rejected",
}

# Confidence policy thresholds (Phase 4 spec).
THRESHOLD_AUTO_VALIDATED = 0.80
THRESHOLD_NEEDS_REVIEW = 0.55
# Engineer brief §8 — publishing discipline: no publish below this confidence.
MIN_PUBLISH_CONFIDENCE = 0.70


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Outcome of validating a candidate rule.

    `valid` means it passes hard required-field checks. `errors` are blockers,
    `warnings` are softer signals (missing operational fields, weak source
    evidence, etc.) that downgrade confidence but don't reject the rule.
    """

    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggested_review_status: str = "draft"
    adjusted_confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "suggested_review_status": self.suggested_review_status,
            "adjusted_confidence": self.adjusted_confidence,
        }


@dataclass
class ConflictReport:
    duplicate_of: Optional[str] = None  # rule_id of an existing duplicate
    conflicting_rule_ids: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        return bool(self.duplicate_of) or bool(self.conflicting_rule_ids)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _norm_title(s: str) -> str:
    """Lowercased, whitespace/punct-collapsed title for dedup matching."""
    s = (s or "").lower().strip()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _list_or_empty(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value).strip()]


def _setify(values: Iterable[str]) -> set[str]:
    return {v.strip().lower() for v in values if v and v.strip()}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_rule_payload(
    payload: dict[str, Any],
    *,
    raw_confidence: float = 0.0,
) -> ValidationResult:
    """Validate a candidate-rule dict (extracted, edited, or manually entered).

    Always returns a `ValidationResult`. Hard failures populate `errors` and
    set `valid=False`. Soft issues populate `warnings` and may downgrade the
    suggested review_status / confidence.
    """
    res = ValidationResult()

    state = (payload.get("state") or "").strip()
    if not state:
        res.errors.append("state is required")

    category = (payload.get("tax_category") or "").strip().lower()
    if not category:
        res.errors.append("tax_category is required")
    elif category not in VALID_TAX_CATEGORIES:
        res.errors.append(
            f"tax_category '{category}' not in {sorted(VALID_TAX_CATEGORIES)}"
        )

    title = (payload.get("rule_title") or "").strip()
    if not title:
        res.errors.append("rule_title is required")
    elif len(title) < 6:
        res.warnings.append("rule_title is very short (< 6 chars)")

    summary = (payload.get("rule_summary") or "").strip()
    if not summary:
        res.errors.append("rule_summary is required")
    elif len(summary) < 20:
        res.warnings.append("rule_summary is very short (< 20 chars)")

    # Source evidence: must have at least one of source_id, source_url, or
    # source_document_name AND a snippet that's substantive.
    has_source_ref = any(
        payload.get(k) for k in ("source_id", "source_url", "source_document_name")
    )
    snippet = (payload.get("source_snippet") or "").strip()
    if not has_source_ref:
        res.errors.append(
            "source evidence required (source_id, source_url, or source_document_name)"
        )
    if not snippet:
        res.warnings.append("missing source_snippet (no verbatim evidence)")
    elif len(snippet) < 40:
        res.warnings.append("source_snippet is very short (< 40 chars)")

    workflow_stage = (payload.get("workflow_stage") or "").strip().lower()
    if workflow_stage and workflow_stage not in VALID_WORKFLOW_STAGES:
        res.warnings.append(
            f"workflow_stage '{workflow_stage}' not in {sorted(VALID_WORKFLOW_STAGES)}"
        )

    submission_method = (payload.get("submission_method") or "").strip().lower()
    if submission_method and submission_method not in VALID_SUBMISSION_METHODS:
        res.warnings.append(
            f"submission_method '{submission_method}' not in {sorted(VALID_SUBMISSION_METHODS)}"
        )

    # Operational completeness — soft. We want extracted rules to carry at
    # least one of: required_actions, required_forms, deadlines.
    op_signals = sum(
        1
        for k in ("required_actions", "required_forms", "deadlines")
        if _list_or_empty(payload.get(k))
    )
    if op_signals == 0:
        res.warnings.append(
            "rule has no required_actions / required_forms / deadlines (operational thinness)"
        )

    res.valid = not res.errors

    # ---- Confidence adjustment ----
    adj = max(0.0, min(float(raw_confidence or 0.0), 1.0))
    if not snippet:
        adj -= 0.10
    elif len(snippet) < 80:
        adj -= 0.05
    if op_signals == 0:
        adj -= 0.05
    if op_signals >= 2:
        adj += 0.05
    if not res.valid:
        adj -= 0.20
    adj = max(0.0, min(adj, 1.0))
    res.adjusted_confidence = round(adj, 4)

    res.suggested_review_status = compute_review_status(adj, res)
    return res


def compute_review_status(confidence: float, result: ValidationResult) -> str:
    """Map (confidence, validation) → review_status.

    Strict policy: invalid rules can never be auto_validated. Borderline
    confidence always lands in needs_review so a human can sign off.
    """
    if not result.valid:
        return "draft"
    if result.errors:
        return "draft"
    if confidence >= THRESHOLD_AUTO_VALIDATED and not result.warnings:
        return "auto_validated"
    if confidence >= THRESHOLD_AUTO_VALIDATED and result.warnings:
        return "needs_review"
    if confidence >= THRESHOLD_NEEDS_REVIEW:
        return "needs_review"
    return "draft"


def can_publish(rule: models.Rule) -> tuple[bool, list[str]]:
    """Hard gate for the ``publish`` review action (brief §7–§8 governance).

    Requires: schema validation pass, minimum confidence, and **human
    ``approved``** (or idempotent re-publish when already ``published``).
    ``auto_validated`` alone is not enough — an explicit approve step records
    reviewer intent in the audit trail.
    """
    payload = _rule_to_payload(rule)
    res = validate_rule_payload(payload, raw_confidence=rule.confidence_score)
    blockers: list[str] = []
    if not res.valid:
        blockers.extend(res.errors)
    st = rule.review_status
    if st == "published":
        pass
    elif st != "approved":
        blockers.append(
            "publish requires human approve first (review_status must be 'approved')"
        )
    if rule.confidence_score < MIN_PUBLISH_CONFIDENCE:
        blockers.append(
            f"confidence {rule.confidence_score:.2f} is below minimum "
            f"{MIN_PUBLISH_CONFIDENCE:.2f} for publishing"
        )
    # Optional governance (effective_date, lineage) via settings.strict_publish_checks.
    from . import governance_service

    blockers.extend(governance_service.strict_publish_blockers(rule))
    return (not blockers), blockers


def _rule_to_payload(rule: models.Rule) -> dict[str, Any]:
    return {
        "tenant_id": rule.tenant_id,
        "state": rule.state,
        "tax_category": rule.tax_category,
        "rule_title": rule.rule_title,
        "rule_summary": rule.rule_summary,
        "workflow_stage": rule.workflow_stage,
        "submission_method": rule.submission_method,
        "required_actions": rule.required_actions,
        "required_forms": rule.required_forms,
        "deadlines": rule.deadlines,
        "source_id": rule.source_id,
        "source_url": rule.source_url,
        "source_document_name": rule.source_document_name,
        "source_snippet": rule.source_snippet,
        "program_variant": rule.program_variant,
        "effective_date": rule.effective_date,
        "effective_date_end": rule.effective_date_end,
    }


# ---------------------------------------------------------------------------
# Duplicate / conflict detection
# ---------------------------------------------------------------------------


def find_duplicate_rule(
    db: Session,
    *,
    tenant_id: str = "default",
    state: str,
    tax_category: str,
    rule_title: str,
    exclude_rule_id: Optional[str] = None,
) -> Optional[models.Rule]:
    """Match by (state, tax_category, normalized title)."""
    if not (state and tax_category and rule_title):
        return None
    target = _norm_title(rule_title)
    if not target:
        return None
    q = (
        db.query(models.Rule)
        .filter(models.Rule.tenant_id == tenant_id)
        .filter(models.Rule.state == state)
        .filter(models.Rule.tax_category == tax_category)
    )
    if exclude_rule_id:
        q = q.filter(models.Rule.id != exclude_rule_id)
    for r in q.all():
        if _norm_title(r.rule_title) == target:
            return r
    return None


def find_conflicting_rules(
    db: Session,
    *,
    candidate: dict[str, Any],
    exclude_rule_id: Optional[str] = None,
    limit: int = 5,
) -> list[models.Rule]:
    """Same (state, category, rule_category) but different operational fields.

    Conflict heuristic: any disagreement in the union of forms, deadlines,
    or required_actions sets.
    """
    state = candidate.get("state")
    category = candidate.get("tax_category")
    rule_category = candidate.get("rule_category")
    if not (state and category):
        return []

    tenant_id = str(candidate.get("tenant_id") or "default")
    q = (
        db.query(models.Rule)
        .filter(models.Rule.tenant_id == tenant_id)
        .filter(models.Rule.state == state)
        .filter(models.Rule.tax_category == category)
    )
    if rule_category:
        q = q.filter(models.Rule.rule_category == rule_category)
    if exclude_rule_id:
        q = q.filter(models.Rule.id != exclude_rule_id)

    cand_forms = _setify(_list_or_empty(candidate.get("required_forms")))
    cand_deadlines = _setify(_list_or_empty(candidate.get("deadlines")))
    cand_actions = _setify(_list_or_empty(candidate.get("required_actions")))

    out: list[models.Rule] = []
    for r in q.limit(50).all():
        existing_forms = _setify(_list_or_empty(r.required_forms))
        existing_deadlines = _setify(_list_or_empty(r.deadlines))
        existing_actions = _setify(_list_or_empty(r.required_actions))

        if (
            (cand_forms and existing_forms and cand_forms != existing_forms)
            or (cand_deadlines and existing_deadlines and cand_deadlines != existing_deadlines)
            or (cand_actions and existing_actions and cand_actions != existing_actions)
        ):
            out.append(r)
        if len(out) >= limit:
            break
    return out


def assess_candidate(
    db: Session,
    payload: dict[str, Any],
    *,
    raw_confidence: float = 0.0,
    exclude_rule_id: Optional[str] = None,
) -> tuple[ValidationResult, ConflictReport]:
    """One-stop validate+dedup+conflict check for a candidate rule."""
    res = validate_rule_payload(payload, raw_confidence=raw_confidence)
    report = ConflictReport()
    tenant_id = str(payload.get("tenant_id") or "default")
    dup = find_duplicate_rule(
        db,
        tenant_id=tenant_id,
        state=payload.get("state") or "",
        tax_category=payload.get("tax_category") or "",
        rule_title=payload.get("rule_title") or "",
        exclude_rule_id=exclude_rule_id,
    )
    if dup is not None:
        report.duplicate_of = dup.id
        res.warnings.append(f"duplicate of existing rule {dup.id}")
        # Down-grade confidence + suggest needs_review when duplicate found.
        res.adjusted_confidence = max(0.0, res.adjusted_confidence - 0.10)
        if res.suggested_review_status == "auto_validated":
            res.suggested_review_status = "needs_review"

    conflicts = find_conflicting_rules(
        db, candidate=payload, exclude_rule_id=exclude_rule_id
    )
    if conflicts:
        report.conflicting_rule_ids = [r.id for r in conflicts]
        res.warnings.append(
            f"conflicts with {len(conflicts)} existing rule(s) "
            f"on forms/deadlines/required_actions"
        )
        if res.suggested_review_status == "auto_validated":
            res.suggested_review_status = "needs_review"

    return res, report
