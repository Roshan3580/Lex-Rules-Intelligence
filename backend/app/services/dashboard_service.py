"""Dashboard aggregates: KPIs, unified activity timeline, actionable alerts (Phase 9)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from .. import models
from ..services import admin_service, validation


def _activity_id(*parts: str) -> str:
    h = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]
    return f"act-{h}"


def _review_action_label(action: str) -> str:
    return {
        "approve": "Rule approved",
        "reject": "Rule rejected",
        "publish": "Rule published",
        "needs_review": "Rule sent to review",
        "edit": "Rule edited",
    }.get(action, action.replace("_", " ").title())


def build_activities(db: Session, *, limit: int = 40) -> list[dict[str, Any]]:
    """Merge ingestion, review, source-version, and extraction signals."""
    cap = min(max(limit, 1), 80)
    items: list[dict[str, Any]] = []

    rev_rows = (
        db.query(models.ReviewEvent, models.Rule)
        .join(models.Rule, models.ReviewEvent.rule_id == models.Rule.id)
        .order_by(models.ReviewEvent.created_at.desc())
        .limit(28)
        .all()
    )
    for ev, rule in rev_rows:
        label = _review_action_label(ev.action)
        detail = rule.rule_title
        ctx_parts = [rule.state, rule.tax_category]
        if ev.actor:
            ctx_parts.insert(0, str(ev.actor))
        ctx = " · ".join(ctx_parts)
        kind = (
            "approved"
            if ev.action in ("approve", "publish")
            else "flagged"
            if ev.action in ("reject", "needs_review")
            else "updated"
            if ev.action == "edit"
            else "review"
        )
        conf = int(round(rule.confidence_score * 100)) if rule.confidence_score else None
        items.append(
            {
                "id": _activity_id("rev", ev.id),
                "kind": kind,
                "title": label,
                "detail": detail,
                "context": ctx,
                "confidence_pct": conf,
                "ref_type": "rule",
                "ref_id": rule.id,
                "created_at": ev.created_at,
            }
        )

    runs = (
        db.query(models.IngestionRun)
        .order_by(models.IngestionRun.started_at.desc())
        .limit(12)
        .all()
    )
    for run in runs:
        note = f"{run.ingested} ingested"
        if run.errors:
            note += f", {run.errors} errors"
        if run.duplicates:
            note += f", {run.duplicates} duplicates"
        items.append(
            {
                "id": _activity_id("run", run.id),
                "kind": "ingestion_run",
                "title": f"Ingestion run ({run.kind}) — {run.status}",
                "detail": note + (f" of {run.total}" if run.total else ""),
                "context": run.id[:8],
                "confidence_pct": None,
                "ref_type": "ingestion_run",
                "ref_id": run.id,
                "created_at": run.finished_at or run.started_at,
            }
        )

    run_items = (
        db.query(models.IngestionRunItem)
        .filter(models.IngestionRunItem.rules_created > 0)
        .order_by(models.IngestionRunItem.created_at.desc())
        .limit(18)
        .all()
    )
    for it in run_items:
        label = it.name or it.url or "Source"
        items.append(
            {
                "id": _activity_id("item", it.id),
                "kind": "extracted",
                "title": f"Extracted {it.rules_created} rule(s)",
                "detail": label[:200],
                "context": (it.state or "—") + (f" · {it.tax_category}" if it.tax_category else ""),
                "confidence_pct": None,
                "ref_type": "source" if it.source_id else None,
                "ref_id": it.source_id,
                "created_at": it.created_at,
            }
        )

    versions = (
        db.query(models.SourceVersion)
        .filter(models.SourceVersion.captured_reason == "content_changed")
        .order_by(models.SourceVersion.created_at.desc())
        .limit(12)
        .all()
    )
    for sv in versions:
        title = sv.title or sv.canonical_url or sv.source_id[:8]
        items.append(
            {
                "id": _activity_id("sv", sv.id),
                "kind": "source_updated",
                "title": "Source content changed",
                "detail": title[:220],
                "context": f"v{sv.version}",
                "confidence_pct": None,
                "ref_type": "source",
                "ref_id": sv.source_id,
                "created_at": sv.created_at,
            }
        )

    items.sort(key=lambda x: x["created_at"] or datetime.min, reverse=True)
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in items:
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        out.append(row)
        if len(out) >= cap:
            break
    return out


def build_alerts(db: Session, *, summary: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    """Derive actionable alerts from live rows (not mocked)."""
    alerts: list[dict[str, Any]] = []
    sid = 0

    def add(
        severity: str,
        title: str,
        body: str,
        ref_type: Optional[str] = None,
        ref_id: Optional[str] = None,
    ) -> None:
        nonlocal sid
        sid += 1
        alerts.append(
            {
                "id": f"alert-{sid}",
                "severity": severity,
                "title": title,
                "body": body,
                "ref_type": ref_type,
                "ref_id": ref_id,
            }
        )

    sumry = summary or admin_service.admin_summary(db)
    failed = (
        db.query(models.Source)
        .filter(models.Source.status == "failed")
        .order_by(models.Source.updated_at.desc())
        .limit(8)
        .all()
    )
    for src in failed:
        add(
            "error",
            f"Ingestion failed: {src.name[:80]}",
            (src.error_message or "See Sources for details.")[:400],
            "source",
            src.id,
        )

    nir = int(sumry.get("rules_in_review", 0))
    if nir > 0:
        add(
            "info",
            f"{nir} rule(s) need review",
            "Open the Review queue to approve, reject, or publish.",
        )

    low_conf = (
        db.query(models.Rule)
        .filter(models.Rule.confidence_score < validation.THRESHOLD_NEEDS_REVIEW)
        .filter(
            models.Rule.review_status.in_(
                ["draft", "needs_review", "auto_validated"]
            )
        )
        .count()
    )
    if low_conf > 0:
        add(
            "warning",
            f"{low_conf} rule(s) below confidence threshold",
            f"Rules under {int(validation.THRESHOLD_NEEDS_REVIEW * 100)}% confidence while not published should be checked.",
        )

    conflict_lineage = 0
    for rule in (
        db.query(models.Rule)
        .filter(models.Rule.lineage.isnot(None))
        .limit(500)
        .all()
    ):
        lineage = rule.lineage or {}
        cr = lineage.get("conflicting_rule_ids") or lineage.get("conflicts")
        if cr:
            conflict_lineage += 1
    if conflict_lineage > 0:
        add(
            "warning",
            "Potential rule conflicts flagged",
            f"{conflict_lineage} rule(s) carry conflict metadata from extraction. Validate in Review.",
        )

    dup_pairs = 0
    recent = (
        db.query(models.Rule)
        .order_by(models.Rule.created_at.desc())
        .limit(120)
        .all()
    )
    seen: set[tuple[str, str]] = set()
    for rule in recent:
        dup = validation.find_duplicate_rule(
            db,
            state=rule.state,
            tax_category=rule.tax_category,
            rule_title=rule.rule_title,
            exclude_rule_id=rule.id,
        )
        if dup:
            pair = tuple(sorted([rule.id, dup.id]))
            if pair not in seen:
                seen.add(pair)
                dup_pairs += 1
    if dup_pairs > 0:
        add(
            "warning",
            f"{dup_pairs} duplicate rule title pair(s) detected",
            "Same state, category, and normalized title as another rule — review for consolidation.",
        )

    changed_recent = (
        db.query(models.SourceVersion)
        .filter(models.SourceVersion.captured_reason == "content_changed")
        .order_by(models.SourceVersion.created_at.desc())
        .limit(1)
        .first()
    )
    cutoff = datetime.utcnow() - timedelta(days=7)
    if changed_recent and changed_recent.created_at >= cutoff:
        add(
            "info",
            "Source content changed (last 7 days)",
            "At least one indexed source had a checksum change. Re-extraction may have run; check Activity.",
            "source",
            changed_recent.source_id,
        )

    return alerts
