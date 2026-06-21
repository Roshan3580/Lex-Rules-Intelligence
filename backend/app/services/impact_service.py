"""Source change → affected rules and re-ingest recommendations."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from .. import models


def analyze_source_impact(db: Session, *, source_id: str) -> dict[str, Any]:
    """Return rules tied to a source; flag those likely needing human review."""
    rules = db.query(models.Rule).filter(models.Rule.source_id == source_id).all()
    out = []
    for r in rules:
        out.append(
            {
                "rule_id": r.id,
                "rule_title": r.rule_title[:120],
                "review_status": r.review_status,
                "recommendation": (
                    "needs_review"
                    if r.review_status in ("published", "approved")
                    else "auto_update_safe_candidate"
                ),
            }
        )
    return {
        "source_id": source_id,
        "rules_affected": len(out),
        "items": out[:80],
        "embedding_diff": "checksum-only in v1 — enable semantic_delta when embeddings on",
    }
