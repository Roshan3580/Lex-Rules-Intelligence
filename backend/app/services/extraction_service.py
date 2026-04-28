"""Rule extraction service.

Given an ingested Source (with chunked text), produce candidate Rule rows.
We use a hybrid strategy:

1. If an LLM is configured, send chunks (in batches) to the model with a
   strict JSON schema asking for normalized rule objects, then validate +
   persist them with `auto_validated` or `needs_review` review_status
   depending on confidence.

2. If no LLM is configured we use a deterministic keyword/heuristic
   extractor. It is intentionally conservative: every emitted rule cites
   the original snippet, gets a moderate confidence score, and is marked
   `needs_review` so a human can refine it.

Either way, the rules are traceable back to the source via source_id +
source_snippet + source_url.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from sqlalchemy.orm import Session

from .. import models
from ..utils.llm_client import llm_client

logger = logging.getLogger(__name__)


# Keywords used by both LLM prompt and the deterministic fallback to detect
# which tax category a chunk most likely relates to.
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "sales_tax": [
        "sales tax", "use tax", "seller's permit", "resale certificate",
        "remote seller", "marketplace facilitator", "sales and use",
    ],
    "payroll_tax": [
        "payroll tax", "unemployment insurance", "ui tax", "sui",
        "employer payroll", "futa", "suta", "wage report",
    ],
    "corporate_tax": [
        "corporate income tax", "corporate tax", "c corporation",
        "corporate franchise", "corporate excise",
    ],
    "income_tax": [
        "personal income tax", "individual income tax", "state income tax",
    ],
    "withholding": [
        "withholding tax", "employer withholding", "withholding allowance",
        "wage withholding", "withholding return",
    ],
    "franchise_tax": [
        "franchise tax", "annual franchise", "margin tax",
    ],
}

DEADLINE_RE = re.compile(
    r"(?:by|on|before|due\s+(?:by|on)?)?\s*"
    r"((?:January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s*\d{4})?|"
    r"\d{1,2}/\d{1,2}(?:/\d{2,4})?|"
    r"(?:quarterly|monthly|annually|semi-?annually|each\s+quarter))",
    re.IGNORECASE,
)

FORM_RE = re.compile(r"\bForm\s+([A-Z0-9][A-Z0-9-]{1,15})\b")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def extract_rules_for_source(
    db: Session, source: models.Source
) -> tuple[int, str]:
    """Extract candidate rules from a Source's chunks. Returns (count, method)."""
    chunks = (
        db.query(models.SourceChunk)
        .filter(models.SourceChunk.source_id == source.id)
        .order_by(models.SourceChunk.chunk_index)
        .all()
    )
    if not chunks:
        return 0, "none"

    if llm_client.enabled:
        try:
            count = _extract_with_llm(db, source, chunks)
            return count, "llm"
        except Exception as exc:  # pragma: no cover
            logger.warning("LLM extraction failed, falling back: %s", exc)

    count = _extract_with_heuristics(db, source, chunks)
    return count, "heuristic"


# ---------------------------------------------------------------------------
# LLM-based extraction
# ---------------------------------------------------------------------------


_LLM_SYSTEM = (
    "You are a tax-policy analyst extracting structured rules from US "
    "state tax source documents. You must only output rules that are "
    "clearly supported by the provided text. Do not invent forms, "
    "deadlines, or thresholds. If the text does not contain a clear "
    "rule, return an empty list."
)


def _llm_prompt(state: Optional[str], category: Optional[str], chunk_text: str) -> str:
    return (
        f"State context: {state or 'unknown'}\n"
        f"Tax category context: {category or 'unknown'}\n\n"
        "From the SOURCE TEXT below, extract a JSON object of the form:\n"
        '{ "rules": [ {\n'
        '  "state": "<US state name>",\n'
        '  "tax_category": "sales_tax|payroll_tax|corporate_tax|income_tax|withholding|franchise_tax|other",\n'
        '  "rule_title": "short title",\n'
        '  "rule_summary": "1-3 sentence plain-English summary",\n'
        '  "detailed_rule": "longer explanation if helpful",\n'
        '  "conditions": ["..."],\n'
        '  "required_actions": ["..."],\n'
        '  "required_forms": ["Form ABC-123"],\n'
        '  "deadlines": ["April 15"],\n'
        '  "exceptions": ["..."],\n'
        '  "effective_date": "optional ISO date or year",\n'
        '  "source_snippet": "verbatim sentence(s) from the source",\n'
        '  "confidence_score": 0.0\n'
        "} ] }\n\n"
        "Rules:\n"
        "- Only include rules clearly supported by the text.\n"
        "- source_snippet must be a literal substring of the SOURCE TEXT.\n"
        "- confidence_score in [0,1].\n"
        "- If unclear, return an empty rules array.\n\n"
        f"SOURCE TEXT:\n\"\"\"\n{chunk_text}\n\"\"\""
    )


def _extract_with_llm(
    db: Session,
    source: models.Source,
    chunks: list[models.SourceChunk],
) -> int:
    """Iterate chunks and ask the LLM for normalized rules.

    For cost control we group small chunks together until a soft char
    budget. This is a prototype; a production implementation would batch
    far more aggressively and cache by (source_checksum, prompt_version).
    """
    BATCH_CHARS = 4000
    batches: list[str] = []
    current = ""
    for c in chunks:
        if len(current) + len(c.text) > BATCH_CHARS and current:
            batches.append(current)
            current = c.text
        else:
            current = (current + "\n\n" + c.text).strip()
    if current:
        batches.append(current)

    created = 0
    for batch in batches:
        try:
            data = llm_client.chat_json(
                [
                    {"role": "system", "content": _LLM_SYSTEM},
                    {
                        "role": "user",
                        "content": _llm_prompt(source.state, source.tax_category, batch),
                    },
                ],
                temperature=0.1,
                max_tokens=1500,
            )
        except Exception as exc:
            logger.warning("LLM call failed for one batch: %s", exc)
            continue

        if not data or not isinstance(data, dict):
            continue

        for rule_dict in data.get("rules", []) or []:
            if not isinstance(rule_dict, dict):
                continue
            rule = _persist_llm_rule(db, source, rule_dict)
            if rule is not None:
                created += 1

    db.flush()
    return created


def _persist_llm_rule(
    db: Session, source: models.Source, rule_dict: dict[str, Any]
) -> Optional[models.Rule]:
    title = (rule_dict.get("rule_title") or "").strip()
    summary = (rule_dict.get("rule_summary") or "").strip()
    snippet = (rule_dict.get("source_snippet") or "").strip()
    if not title or not summary:
        return None

    try:
        confidence = float(rule_dict.get("confidence_score") or 0.6)
    except (TypeError, ValueError):
        confidence = 0.6
    confidence = max(0.0, min(confidence, 1.0))

    review_status = "auto_validated" if confidence >= 0.75 else "needs_review"

    rule = models.Rule(
        state=(rule_dict.get("state") or source.state or "Unknown"),
        tax_category=(rule_dict.get("tax_category") or source.tax_category or "other"),
        rule_title=title[:480],
        rule_summary=summary,
        detailed_rule=rule_dict.get("detailed_rule"),
        conditions=_as_list(rule_dict.get("conditions")),
        required_actions=_as_list(rule_dict.get("required_actions")),
        required_forms=_as_list(rule_dict.get("required_forms")),
        deadlines=_as_list(rule_dict.get("deadlines")),
        exceptions=_as_list(rule_dict.get("exceptions")),
        source_id=source.id,
        source_url=source.url,
        source_document_name=source.name,
        source_snippet=snippet[:2000] if snippet else None,
        effective_date=rule_dict.get("effective_date"),
        confidence_score=confidence,
        review_status=review_status,
        extraction_method="llm",
    )
    db.add(rule)
    return rule


def _as_list(value: Any) -> Optional[list[str]]:
    if value is None:
        return None
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return None


# ---------------------------------------------------------------------------
# Heuristic / fallback extraction
# ---------------------------------------------------------------------------


def _classify_category(text: str, default: Optional[str]) -> str:
    lowered = text.lower()
    best: Optional[tuple[str, int]] = None
    for cat, kws in CATEGORY_KEYWORDS.items():
        score = sum(lowered.count(k) for k in kws)
        if score > 0 and (best is None or score > best[1]):
            best = (cat, score)
    if best:
        return best[0]
    return default or "other"


def _extract_with_heuristics(
    db: Session,
    source: models.Source,
    chunks: list[models.SourceChunk],
) -> int:
    """Build rules from chunks that mention tax-rule-shaped patterns.

    A chunk is promoted to a rule if it (a) hits a tax-category keyword
    AND (b) contains either a Form reference, a deadline phrase, or a
    requirement verb (must/required/shall). This biases toward chunks that
    actually express obligations rather than narrative prose.
    """
    state_default = source.state or "Unknown"
    created = 0

    for chunk in chunks:
        text = chunk.text
        lowered = text.lower()

        category = _classify_category(text, source.tax_category)

        forms = sorted({f"Form {m.group(1)}" for m in FORM_RE.finditer(text)})
        deadlines = sorted({m.group(1).strip() for m in DEADLINE_RE.finditer(text)})

        has_obligation = bool(
            re.search(r"\b(must|required|shall|are required to|file|register)\b", lowered)
        )
        has_signal = bool(forms) or bool(deadlines) or has_obligation
        if not has_signal:
            continue

        if not any(
            kw in lowered for kws in CATEGORY_KEYWORDS.values() for kw in kws
        ):
            continue

        title = _derive_title(text, category, state_default)
        summary = _derive_summary(text)

        rule = models.Rule(
            state=state_default,
            tax_category=category,
            rule_title=title,
            rule_summary=summary,
            detailed_rule=text[:2000],
            conditions=None,
            required_actions=_extract_actions(text),
            required_forms=forms or None,
            deadlines=deadlines or None,
            exceptions=None,
            source_id=source.id,
            source_url=source.url,
            source_document_name=source.name,
            source_snippet=text[:1200],
            confidence_score=0.45,
            review_status="needs_review",
            extraction_method="heuristic",
        )
        db.add(rule)
        created += 1

    db.flush()
    return created


def _derive_title(text: str, category: str, state: str) -> str:
    pretty = category.replace("_", " ").title()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    first = (sentences[0] if sentences else text)[:120].strip()
    if first:
        return f"{state} {pretty}: {first.rstrip('.')}"
    return f"{state} {pretty}"


def _derive_summary(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    summary = " ".join(sentences[:2]).strip()
    return summary[:600] or text[:600]


def _extract_actions(text: str) -> Optional[list[str]]:
    actions = []
    for pattern in (
        r"(must\s+[^.]+\.)",
        r"(required to\s+[^.]+\.)",
        r"(shall\s+[^.]+\.)",
        r"(file\s+[^.]+\.)",
    ):
        for m in re.finditer(pattern, text, re.IGNORECASE):
            phrase = m.group(1).strip()
            if 10 < len(phrase) < 240:
                actions.append(phrase)
    actions = list(dict.fromkeys(actions))[:6]
    return actions or None
