"""Version snapshots for sources and rules.

Phase 3 in the upgrade plan. Whenever a source's content changes (checksum
diff on re-fetch) or a rule is edited / re-extracted / acted on by a
reviewer we capture an immutable snapshot row. The current row in
`sources` / `rules` always represents the latest state; history lives in
`source_versions` / `rule_versions`.

Both helpers are best-effort and never raise — version capture failures
should not block ingestion or admin actions.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable, Optional

from sqlalchemy.orm import Session

from .. import models

logger = logging.getLogger(__name__)


# Fields whose changes we want to track on Rule. Keeping this list explicit
# (vs. reflecting the column list) keeps audit diffs stable when we add
# operational columns later.
RULE_TRACKED_FIELDS: tuple[str, ...] = (
    "state",
    "tax_category",
    "rule_category",
    "workflow_stage",
    "operating_scenario",
    "condition_logic",
    "submission_method",
    "program_variant",
    "rule_title",
    "rule_summary",
    "detailed_rule",
    "conditions",
    "required_actions",
    "required_forms",
    "required_documentation",
    "deadlines",
    "exceptions",
    "source_url",
    "source_document_name",
    "source_snippet",
    "effective_date",
    "effective_date_end",
    "confidence_score",
    "review_status",
    "extraction_method",
)


# ---------------------------------------------------------------------------
# Source versions
# ---------------------------------------------------------------------------


def _next_source_version(db: Session, source_id: str) -> int:
    last = (
        db.query(models.SourceVersion)
        .filter(models.SourceVersion.source_id == source_id)
        .order_by(models.SourceVersion.version.desc())
        .first()
    )
    return (last.version + 1) if last is not None else 1


def capture_source_version(
    db: Session,
    source: models.Source,
    *,
    reason: str = "initial",
) -> Optional[models.SourceVersion]:
    """Snapshot the current state of a Source.

    Returns the new SourceVersion row, or None if capture failed.
    """
    try:
        version = _next_source_version(db, source.id)
        sv = models.SourceVersion(
            source_id=source.id,
            version=version,
            checksum=source.checksum,
            canonical_url=source.canonical_url,
            title=source.name,
            raw_text=source.raw_text,
            status_at_capture=source.status,
            captured_reason=reason,
        )
        db.add(sv)
        source.current_version = version
        db.flush()
        return sv
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to capture source version for %s: %s", source.id, exc)
        return None


# ---------------------------------------------------------------------------
# Rule versions
# ---------------------------------------------------------------------------


def _next_rule_version(db: Session, rule_id: str) -> int:
    last = (
        db.query(models.RuleVersion)
        .filter(models.RuleVersion.rule_id == rule_id)
        .order_by(models.RuleVersion.version.desc())
        .first()
    )
    return (last.version + 1) if last is not None else 1


def serialize_rule(rule: models.Rule, fields: Iterable[str] = RULE_TRACKED_FIELDS) -> dict[str, Any]:
    """Pluck the tracked field values off a rule into a JSON-safe dict."""
    out: dict[str, Any] = {}
    for f in fields:
        out[f] = getattr(rule, f, None)
    return out


def diff_rule_payloads(
    previous: dict[str, Any],
    new: dict[str, Any],
    fields: Iterable[str] = RULE_TRACKED_FIELDS,
) -> list[str]:
    """Return list of field names whose values differ between two snapshots."""
    changed: list[str] = []
    for f in fields:
        if previous.get(f) != new.get(f):
            changed.append(f)
    return changed


def capture_rule_version(
    db: Session,
    rule: models.Rule,
    *,
    previous_data: dict[str, Any],
    new_data: Optional[dict[str, Any]] = None,
    reason: str = "edit",
    actor: Optional[str] = None,
    notes: Optional[str] = None,
    extraction_method: Optional[str] = None,
    source_version_id: Optional[str] = None,
) -> Optional[models.RuleVersion]:
    """Create a RuleVersion if any tracked field changed.

    For initial captures (`reason="initial"`) we store regardless of diff
    so every rule has at least one version row.
    """
    try:
        snapshot_new = new_data if new_data is not None else serialize_rule(rule)
        changed = diff_rule_payloads(previous_data, snapshot_new)
        if not changed and reason != "initial":
            return None

        version = _next_rule_version(db, rule.id)
        rv = models.RuleVersion(
            rule_id=rule.id,
            version=version,
            previous_data=previous_data,
            new_data=snapshot_new,
            changed_fields=changed,
            extraction_method=extraction_method or rule.extraction_method,
            source_version_id=source_version_id,
            actor=actor,
            notes=notes,
            captured_reason=reason,
        )
        db.add(rv)
        rule.current_version = version
        db.flush()
        return rv
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to capture rule version for %s: %s", rule.id, exc)
        return None


def latest_source_version(db: Session, source_id: str) -> Optional[models.SourceVersion]:
    return (
        db.query(models.SourceVersion)
        .filter(models.SourceVersion.source_id == source_id)
        .order_by(models.SourceVersion.version.desc())
        .first()
    )
