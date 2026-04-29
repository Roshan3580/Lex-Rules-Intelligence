"""Governance catalog + publish completeness (Brief §6, §8)."""

from __future__ import annotations

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
    """Extra gates when ``settings.strict_publish_checks`` is enabled."""
    if not getattr(settings, "strict_publish_checks", False):
        return []
    out: list[str] = []
    if not (rule.effective_date or "").strip():
        out.append("governance: effective_date (valid_time) required for publish")
    return out
