"""Outcome / rejection events and coverage classification (no LLM)."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from . import rule_engine


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def _reason_tokens(reason: str) -> set[str]:
    return {
        _norm(w)
        for w in re.split(r"\s+", reason.lower())
        if len(_norm(w)) >= 4
    }


def _rule_match_text(rule: models.Rule) -> str:
    parts: list[str] = [
        rule.rule_title or "",
        rule.rule_summary or "",
        rule.detailed_rule or "",
    ]
    for lst in (
        rule.required_forms,
        rule.required_documentation,
        rule.required_actions,
    ):
        if lst:
            parts.extend(str(x) for x in lst)
    return " ".join(parts)


def _score_rule_against_reason(rule: models.Rule, tokens: set[str]) -> float:
    if not tokens:
        return 0.0
    blob = _norm(_rule_match_text(rule))
    hits = sum(1 for t in tokens if t and t in blob)
    return hits / max(len(tokens), 1)


def _payload_hint_tokens(payload: Optional[dict[str, Any]]) -> set[str]:
    if not payload:
        return set()
    out: set[str] = set()
    for key in ("documents", "forms", "attachments"):
        v = payload.get(key)
        if isinstance(v, list):
            for x in v:
                out.add(_norm(str(x)))
        elif isinstance(v, str) and v.strip():
            for part in v.split(","):
                out.add(_norm(part.strip()))
    return {x for x in out if len(x) >= 3}


def match_rules_for_outcome(
    db: Session,
    *,
    state: str,
    tax_category: str,
    workflow_stage: Optional[str],
    rejection_reason: str,
    payload: Optional[dict[str, Any]],
) -> tuple[list[str], float]:
    """Return heuristic ``matched_rule_ids`` ordered by score and a confidence 0–1."""
    rules, _warn = rule_engine.get_applicable_rules(
        db,
        tenant_id="default",
        state=state,
        tax_category=tax_category,
        workflow_stage=workflow_stage,
    )
    if not rules:
        return [], 0.0

    r_tokens = _reason_tokens(rejection_reason)
    p_tokens = _payload_hint_tokens(payload)
    scored: list[tuple[str, float]] = []
    for r in rules:
        s1 = _score_rule_against_reason(r, r_tokens)
        s2 = 0.0
        if p_tokens:
            blob = _norm(_rule_match_text(r))
            hits = sum(1 for t in p_tokens if t in blob)
            s2 = hits / max(len(p_tokens), 1)
        score = max(s1, s2 * 0.85)
        if score > 0:
            scored.append((r.id, score))

    scored.sort(key=lambda x: -x[1])
    top = [rid for rid, s in scored if s >= 0.12][:12]
    confidence = scored[0][1] if scored else 0.0
    return top, confidence


def classify_coverage(
    *,
    matched_rule_ids: list[str],
    match_confidence: float,
    violation_ids: set[str],
) -> str:
    matched_set = set(matched_rule_ids)
    overlap = matched_set & violation_ids

    if overlap:
        return "prevented_by_existing_rule"

    if matched_set and not violation_ids:
        if match_confidence >= 0.12:
            return "rule_existed_but_not_enforced"
        return "unclear"

    if matched_set and violation_ids and not overlap:
        return "unclear"

    if violation_ids and not matched_set:
        return "unclear"

    return "missing_rule"


def create_outcome(
    db: Session,
    *,
    submission_id: Optional[str],
    state: str,
    tax_category: str,
    workflow_stage: Optional[str],
    effective_date: Optional[str],
    rejection_code: Optional[str],
    rejection_reason: str,
    payload: Optional[dict[str, Any]],
) -> tuple[models.OutcomeEvent, dict[str, Any]]:
    st = rule_engine.normalize_state(state)
    pl = payload or {}
    matched_ids, match_conf = match_rules_for_outcome(
        db,
        state=st,
        tax_category=tax_category,
        workflow_stage=workflow_stage,
        rejection_reason=rejection_reason,
        payload=pl,
    )

    val = rule_engine.validate_submission(
        db,
        tenant_id="default",
        state=st,
        tax_category=tax_category,
        workflow_stage=workflow_stage,
        effective_date=effective_date,
        payload=pl,
    )
    v_ids = {v["rule_id"] for v in val.get("violations", [])}

    coverage = classify_coverage(
        matched_rule_ids=matched_ids,
        match_confidence=match_conf,
        violation_ids=v_ids,
    )

    root = rejection_reason.strip()[:240] if rejection_reason else None

    ev = models.OutcomeEvent(
        submission_id=submission_id,
        state=st,
        tax_category=tax_category,
        workflow_stage=workflow_stage,
        rejection_code=rejection_code,
        rejection_reason=rejection_reason,
        normalized_root_cause=root,
        payload=pl,
        matched_rule_ids=matched_ids or None,
        coverage_status=coverage,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    meta = {
        "validation_at_outcome": {
            "valid": val["valid"],
            "risk_level": val["risk_level"],
            "violation_rule_ids": sorted(v_ids),
        },
    }
    return ev, meta


def list_outcomes(
    db: Session,
    *,
    state: Optional[str],
    tax_category: Optional[str],
    coverage_status: Optional[str],
    limit: int = 100,
) -> list[models.OutcomeEvent]:
    q = db.query(models.OutcomeEvent).order_by(models.OutcomeEvent.created_at.desc())
    if state:
        q = q.filter(
            models.OutcomeEvent.state == rule_engine.normalize_state(state)
        )
    if tax_category:
        q = q.filter(models.OutcomeEvent.tax_category == tax_category)
    if coverage_status:
        q = q.filter(models.OutcomeEvent.coverage_status == coverage_status)
    return q.limit(min(limit, 500)).all()


def rejection_coverage_summary(db: Session) -> dict[str, Any]:
    total = db.query(func.count(models.OutcomeEvent.id)).scalar() or 0
    rows = (
        db.query(
            models.OutcomeEvent.coverage_status,
            func.count(models.OutcomeEvent.id),
        )
        .group_by(models.OutcomeEvent.coverage_status)
        .all()
    )
    by_status = [{"coverage_status": r[0], "count": r[1]} for r in rows]

    prevented = next(
        (r[1] for r in rows if r[0] == "prevented_by_existing_rule"), 0
    )
    coverage_pct = (prevented / total * 100.0) if total else 0.0

    reasons = (
        db.query(
            models.OutcomeEvent.rejection_reason,
            func.count(models.OutcomeEvent.id),
        )
        .group_by(models.OutcomeEvent.rejection_reason)
        .order_by(func.count(models.OutcomeEvent.id).desc())
        .limit(10)
        .all()
    )
    top_reasons = [{"reason": r[0][:500], "count": r[1]} for r in reasons]

    missing = (
        db.query(models.OutcomeEvent)
        .filter(models.OutcomeEvent.coverage_status == "missing_rule")
        .all()
    )
    cluster_counter: Counter[str] = Counter()
    for ev in missing:
        label = (ev.normalized_root_cause or ev.rejection_reason or "")[:120].strip()
        if not label:
            label = "(empty reason)"
        cluster_counter[label] += 1
    clusters = [
        {"label": k, "count": v}
        for k, v in cluster_counter.most_common(8)
    ]

    return {
        "total_outcomes": total,
        "by_coverage_status": by_status,
        "top_rejection_reasons": top_reasons,
        "missing_rule_clusters": clusters,
        "coverage_percentage": round(coverage_pct, 2),
    }


def rejection_patterns_analysis(db: Session) -> dict[str, Any]:
    """Cluster outcomes for analytics (Brief §4.4)."""
    from sqlalchemy import func

    by_state = (
        db.query(
            models.OutcomeEvent.state,
            models.OutcomeEvent.tax_category,
            models.OutcomeEvent.coverage_status,
            func.count(models.OutcomeEvent.id),
        )
        .group_by(
            models.OutcomeEvent.state,
            models.OutcomeEvent.tax_category,
            models.OutcomeEvent.coverage_status,
        )
        .all()
    )
    rows_s = [
        {
            "state": r[0],
            "tax_category": r[1],
            "coverage_status": r[2],
            "count": r[3],
        }
        for r in by_state
    ]
    tot = db.query(func.count(models.OutcomeEvent.id)).scalar() or 0
    prev = (
        db.query(func.count(models.OutcomeEvent.id))
        .filter(
            models.OutcomeEvent.coverage_status == "prevented_by_existing_rule"
        )
        .scalar()
        or 0
    )
    miss = (
        db.query(func.count(models.OutcomeEvent.id))
        .filter(models.OutcomeEvent.coverage_status == "missing_rule")
        .scalar()
        or 0
    )
    uncl = (
        db.query(func.count(models.OutcomeEvent.id))
        .filter(models.OutcomeEvent.coverage_status == "unclear")
        .scalar()
        or 0
    )
    rp = {}
    if tot:
        rp["pct_prevented"] = round(prev / tot * 100.0, 2)
        rp["pct_missed"] = round(miss / tot * 100.0, 2)
        rp["pct_unclear"] = round(uncl / tot * 100.0, 2)
    return {
        "by_state": rows_s[:80],
        "by_tax_category": rows_s[:80],
        "by_coverage": rows_s[:80],
        "rule_coverage_report": rp,
    }
