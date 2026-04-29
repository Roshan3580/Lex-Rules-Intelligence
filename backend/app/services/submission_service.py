"""Submission intelligence: how to submit (Brief §4.2)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from .. import models
from . import rule_engine

ENFORCEMENT = frozenset({"published", "approved"})


def build_submission_path(
    db: Session,
    *,
    state: str,
    tax_category: str,
    workflow_stage: Optional[str] = None,
    transaction_type: Optional[str] = None,
) -> dict[str, Any]:
    """Aggregate portal instructions from published rules."""
    st = rule_engine.normalize_state(state)
    methods: set[str] = set()
    steps: list[str] = []
    required_docs: list[str] = []
    ranked: list[dict[str, Any]] = []
    portal_urls: list[str] = []

    q = (
        db.query(models.Rule)
        .filter(models.Rule.state == st)
        .filter(models.Rule.tax_category == tax_category)
        .filter(models.Rule.review_status.in_(ENFORCEMENT))
    )
    if workflow_stage:
        q = q.filter(
            (models.Rule.workflow_stage == workflow_stage)
            | (models.Rule.workflow_stage.is_(None))
        )
    rules = q.order_by(models.Rule.confidence_score.desc()).limit(25).all()

    for r in rules:
        sm = (r.submission_method or "online_portal").strip()
        methods.add(sm)
        if r.portal_instructions:
            steps.append(r.portal_instructions.strip()[:500])
        elif r.submission_portal_url:
            steps.append(f"Open state portal: {r.submission_portal_url[:200]}")
        if r.submission_portal_url:
            portal_urls.append(r.submission_portal_url)
        elif r.source_url and "http" in (r.source_url or ""):
            portal_urls.append(r.source_url)
        for lst in (r.required_forms or [], r.required_documentation or []):
            for x in lst or []:
                if x and x not in required_docs:
                    required_docs.append(str(x))
        if r.submission_endpoint_urls:
            for u in r.submission_endpoint_urls:
                if u and u not in portal_urls:
                    portal_urls.append(u)
        ranked.append(
            {
                "rule_id": r.id,
                "rule_title": r.rule_title,
                "submission_method": sm,
                "confidence": float(r.confidence_score or 0),
            }
        )

    if not steps and not portal_urls:
        steps = [
            f"Confirm obligations for {st} / {tax_category} in the state's tax authority portal.",
            "Gather required registrations, forms, and schedules before filing.",
            "Submit via the channel your rules require (portal, mail, or EFT).",
        ]

    recommended = (
        "online_portal"
        if "online_portal" in methods or "portal" in methods
        else (next(iter(methods)) if methods else "portal")
    )

    subs = list(methods) if methods else ["portal", "mail"]
    if "fax" not in subs and tax_category == "sales_tax":
        subs.append("fax")

    return {
        "recommended_path": recommended,
        "steps": steps[:12] or ["Review published rules for this state and category."],
        "required_documents": required_docs[:24],
        "submission_methods": sorted(subs),
        "ranked_options": ranked[:10],
        "portal_urls": list(dict.fromkeys(portal_urls))[:8],
        "transaction_type": transaction_type,
    }
