"""Analytics aggregates for the Insights page (Phase 10)."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models


_CONFIDENCE_BIN_LABELS = ["0–20%", "21–40%", "41–60%", "61–80%", "81–100%"]

_FRESHNESS_BUCKETS = [
    ("never_checked", "Never checked"),
    ("0_1d", "≤1 day"),
    ("2_7d", "2–7 days"),
    ("8_30d", "8–30 days"),
    ("31_plus", "31+ days"),
]


def _normalize_extraction(method: str | None) -> str:
    if not method:
        return "unknown"
    m = method.lower()
    if "llm" in m or m == "openai" or m == "groq":
        return "llm"
    if "heuristic" in m or m == "keyword":
        return "heuristic"
    if "manual" in m or m == "ui" or m == "admin":
        return "manual"
    if "seed" in m or "demo" in m:
        return "seed_demo"
    return "other"


def build_analytics(db: Session, *, days: int = 30) -> dict[str, Any]:
    """Return chart-ready bundles; safe on empty DB."""
    window = max(7, min(days, 90))
    cutoff = datetime.utcnow() - timedelta(days=window)

    # --- Rules by state ---
    st_rows = (
        db.query(models.Rule.state, func.count(models.Rule.id))
        .group_by(models.Rule.state)
        .order_by(func.count(models.Rule.id).desc())
        .all()
    )
    rules_by_state = [
        {"state": s or "unknown", "count": int(c)} for s, c in st_rows
    ]

    # --- Rules by tax category ---
    cat_rows = (
        db.query(models.Rule.tax_category, func.count(models.Rule.id))
        .group_by(models.Rule.tax_category)
        .order_by(func.count(models.Rule.id).desc())
        .all()
    )
    rules_by_tax_category = [
        {"category": c or "unknown", "count": int(n)} for c, n in cat_rows
    ]

    # --- Confidence histogram (current rules) ---
    conf_counts = [0, 0, 0, 0, 0]
    for (score,) in db.query(models.Rule.confidence_score).all():
        try:
            x = float(score)
        except (TypeError, ValueError):
            x = 0.0
        idx = min(int(x * 5), 4)
        conf_counts[idx] += 1
    confidence_distribution = [
        {"label": lab, "count": conf_counts[i]} for i, lab in enumerate(_CONFIDENCE_BIN_LABELS)
    ]

    # --- Sources by ingestion status ---
    status_rows = (
        db.query(models.Source.status, func.count(models.Source.id))
        .group_by(models.Source.status)
        .all()
    )
    sources_by_status = {s or "unknown": int(c) for s, c in status_rows}

    # --- Extraction method (normalized) ---
    ext_raw = (
        db.query(models.Rule.extraction_method, func.count(models.Rule.id))
        .group_by(models.Rule.extraction_method)
        .all()
    )
    ext_merged: dict[str, int] = defaultdict(int)
    for method, cnt in ext_raw:
        key = _normalize_extraction(method)
        ext_merged[key] += int(cnt)
    extraction_methods = [
        {"method": k, "count": v} for k, v in sorted(ext_merged.items(), key=lambda x: -x[1])
    ]

    # --- Rules created per day (within window) ---
    day_created = func.date(models.Rule.created_at)
    rules_day_rows = (
        db.query(day_created, func.count(models.Rule.id))
        .filter(models.Rule.created_at >= cutoff)
        .group_by(day_created)
        .all()
    )
    rules_per_day: dict[str, int] = {}
    for dval, cnt in rules_day_rows:
        if dval is None:
            continue
        key = dval if isinstance(dval, str) else dval.isoformat()
        rules_per_day[key] = int(cnt)
    # fill missing days with 0 for chart continuity
    rules_created_by_day: list[dict[str, Any]] = []
    for i in range(window):
        d = (datetime.utcnow() - timedelta(days=window - 1 - i)).date()
        key = d.isoformat()
        rules_created_by_day.append({"date": key, "count": rules_per_day.get(key, 0)})

    # --- Review events per day (proxy for review workload) ---
    day_rev = func.date(models.ReviewEvent.created_at)
    rev_day_rows = (
        db.query(day_rev, func.count(models.ReviewEvent.id))
        .filter(models.ReviewEvent.created_at >= cutoff)
        .group_by(day_rev)
        .all()
    )
    rev_per_day: dict[str, int] = {}
    for dval, cnt in rev_day_rows:
        if dval is None:
            continue
        key = dval if isinstance(dval, str) else dval.isoformat()
        rev_per_day[key] = int(cnt)
    review_events_by_day = []
    for i in range(window):
        d = (datetime.utcnow() - timedelta(days=window - 1 - i)).date()
        key = d.isoformat()
        review_events_by_day.append({"date": key, "count": rev_per_day.get(key, 0)})

    # --- Source freshness (bucket counts) ---
    now = datetime.utcnow()
    fresh_buckets = {k: 0 for k, _ in _FRESHNESS_BUCKETS}
    for src in db.query(models.Source).all():
        lc = src.last_checked
        if lc is None:
            fresh_buckets["never_checked"] += 1
            continue
        try:
            delta = now - lc
            days = max(0, int(delta.total_seconds() // 86400))
        except Exception:
            fresh_buckets["never_checked"] += 1
            continue
        if days <= 1:
            fresh_buckets["0_1d"] += 1
        elif days <= 7:
            fresh_buckets["2_7d"] += 1
        elif days <= 30:
            fresh_buckets["8_30d"] += 1
        else:
            fresh_buckets["31_plus"] += 1
    source_freshness = [
        {"bucket": key, "label": lab, "count": fresh_buckets[key]}
        for key, lab in _FRESHNESS_BUCKETS
    ]

    # --- Source content changes in window (for KPI) ---
    sv_changes = (
        db.query(func.count(models.SourceVersion.id))
        .filter(models.SourceVersion.captured_reason == "content_changed")
        .filter(models.SourceVersion.created_at >= cutoff)
        .scalar()
        or 0
    )

    # --- Totals ---
    total_rules = db.query(func.count(models.Rule.id)).scalar() or 0
    total_sources = db.query(func.count(models.Source.id)).scalar() or 0
    published = (
        db.query(func.count(models.Rule.id))
        .filter(models.Rule.review_status == "published")
        .scalar()
        or 0
    )
    in_review = (
        db.query(func.count(models.Rule.id))
        .filter(
            models.Rule.review_status.in_(
                ["draft", "needs_review", "auto_validated"]
            )
        )
        .scalar()
        or 0
    )
    review_events_in_window = (
        db.query(func.count(models.ReviewEvent.id))
        .filter(models.ReviewEvent.created_at >= cutoff)
        .scalar()
        or 0
    )

    return {
        "rules_by_state": rules_by_state[:25],
        "rules_by_tax_category": rules_by_tax_category,
        "confidence_distribution": confidence_distribution,
        "sources_by_status": sources_by_status,
        "extraction_methods": extraction_methods,
        "rules_created_by_day": rules_created_by_day,
        "review_events_by_day": review_events_by_day,
        "source_freshness": source_freshness,
        "window_days": window,
        "summary": {
            "total_rules": int(total_rules),
            "total_sources": int(total_sources),
            "published_rules": int(published),
            "rules_in_review": int(in_review),
            "rules_created_in_window": sum(r["count"] for r in rules_created_by_day),
            "source_content_changes_in_window": int(sv_changes),
            "review_events_in_window": int(review_events_in_window),
        },
    }
