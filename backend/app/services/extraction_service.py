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
from . import validation, versioning
from .backfill_service import sync_canonical_fields_for_new_rule

PROMPT_VERSION = "v2-phase4"

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


def _program_variant_for_rule(source: models.Source, rule_dict: dict[str, Any]) -> dict[str, Any]:
    """Engineer brief §6 — program / variant metadata tied to the source."""
    base: dict[str, Any] = {}
    if source.state:
        base["jurisdiction"] = source.state
    if source.tax_category:
        base["tax_program"] = source.tax_category
    if source.name:
        base["source_name"] = source.name
    extra = rule_dict.get("program_variant")
    if isinstance(extra, dict):
        merged = {**base}
        for k, v in extra.items():
            merged[str(k)] = v
        return merged
    return base


def _effective_date_end(rule_dict: dict[str, Any]) -> Optional[str]:
    for key in ("effective_date_end", "effective_end", "sunset_date"):
        v = rule_dict.get(key)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s[:64]
    return None


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
            method = "llm"
        except Exception as exc:  # pragma: no cover
            logger.warning("LLM extraction failed, falling back: %s", exc)
            count = _extract_with_heuristics(db, source, chunks)
            method = "heuristic"
    else:
        count = _extract_with_heuristics(db, source, chunks)
        method = "heuristic"

    _capture_initial_rule_versions(db, source)
    return count, method


def _capture_initial_rule_versions(db: Session, source: models.Source) -> None:
    """Snapshot v1 of every rule on this source that doesn't have one yet."""
    rules = db.query(models.Rule).filter(models.Rule.source_id == source.id).all()
    source_version = versioning.latest_source_version(db, source.id)
    sv_id = source_version.id if source_version is not None else None
    for r in rules:
        has_version = (
            db.query(models.RuleVersion)
            .filter(models.RuleVersion.rule_id == r.id)
            .first()
        )
        if has_version is not None:
            continue
        versioning.capture_rule_version(
            db,
            r,
            previous_data={},
            new_data=versioning.serialize_rule(r),
            reason="initial",
            extraction_method=r.extraction_method,
            source_version_id=sv_id,
        )
    db.flush()


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
        '  "rule_category": "registration|filing|payment|exemption|threshold|penalty|other",\n'
        '  "workflow_stage": "intake|verification|documentation|submission|resolution|other",\n'
        '  "operating_scenario": "short description of the taxpayer scenario this rule applies to",\n'
        '  "rule_title": "short title",\n'
        '  "rule_summary": "1-3 sentence plain-English summary",\n'
        '  "detailed_rule": "longer explanation if helpful",\n'
        '  "condition_logic": "structured if/when phrasing of when this rule applies",\n'
        '  "conditions": ["..."],\n'
        '  "required_actions": ["..."],\n'
        '  "required_forms": ["Form ABC-123"],\n'
        '  "required_documentation": ["business license", "EIN letter"],\n'
        '  "submission_method": "online_portal|mail|in_person|eft|phone|other",\n'
        '  "deadlines": ["April 15"],\n'
        '  "exceptions": ["..."],\n'
        '  "effective_date": "optional ISO date or year",\n'
        '  "source_snippet": "verbatim sentence(s) from the source",\n'
        '  "confidence_score": 0.0\n'
        "} ] }\n\n"
        "Rules:\n"
        "- Only include rules clearly supported by the text.\n"
        "- source_snippet MUST be a literal substring of the SOURCE TEXT.\n"
        "- Use the controlled vocabularies above for workflow_stage and submission_method.\n"
        "- Leave fields out (or use null/empty array) if the source does not say.\n"
        "- Do NOT invent forms, deadlines, thresholds, or penalties.\n"
        "- confidence_score in [0,1].\n"
        "- If the chunk does not clearly express an operational rule, return an empty rules array.\n\n"
        f"SOURCE TEXT:\n\"\"\"\n{chunk_text}\n\"\"\""
    )


def _extract_with_llm(
    db: Session,
    source: models.Source,
    chunks: list[models.SourceChunk],
) -> int:
    """Iterate chunks and ask the LLM for normalized rules.

    Chunks are grouped under a soft char budget so a single LLM call covers
    several short chunks. Each batch records its chunk ids so that lineage
    metadata on every emitted rule traces back to the chunks that fed it.
    """
    BATCH_CHARS = 4000
    batches: list[tuple[str, list[str]]] = []  # (concatenated_text, chunk_ids)
    current_text = ""
    current_ids: list[str] = []
    for c in chunks:
        if len(current_text) + len(c.text) > BATCH_CHARS and current_text:
            batches.append((current_text, current_ids))
            current_text = c.text
            current_ids = [c.id]
        else:
            current_text = (current_text + "\n\n" + c.text).strip()
            current_ids.append(c.id)
    if current_text:
        batches.append((current_text, current_ids))

    source_version = versioning.latest_source_version(db, source.id)
    created = 0
    for batch_text, batch_chunk_ids in batches:
        try:
            data = llm_client.chat_json(
                [
                    {"role": "system", "content": _LLM_SYSTEM},
                    {
                        "role": "user",
                        "content": _llm_prompt(source.state, source.tax_category, batch_text),
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
            rule = _persist_llm_rule(
                db,
                source,
                rule_dict,
                chunk_ids=batch_chunk_ids,
                source_version_id=source_version.id if source_version else None,
            )
            if rule is not None:
                created += 1

    db.flush()
    return created


def _persist_llm_rule(
    db: Session,
    source: models.Source,
    rule_dict: dict[str, Any],
    *,
    chunk_ids: Optional[list[str]] = None,
    source_version_id: Optional[str] = None,
) -> Optional[models.Rule]:
    title = (rule_dict.get("rule_title") or "").strip()
    summary = (rule_dict.get("rule_summary") or "").strip()
    snippet = (rule_dict.get("source_snippet") or "").strip()
    if not title or not summary:
        return None

    try:
        confidence_raw = float(rule_dict.get("confidence_score") or 0.6)
    except (TypeError, ValueError):
        confidence_raw = 0.6
    confidence_raw = max(0.0, min(confidence_raw, 1.0))

    payload = {
        "tenant_id": source.tenant_id,
        "state": rule_dict.get("state") or source.state or "Unknown",
        "tax_category": rule_dict.get("tax_category") or source.tax_category or "other",
        "rule_category": (rule_dict.get("rule_category") or "").strip() or None,
        "rule_title": title[:480],
        "rule_summary": summary,
        "workflow_stage": (rule_dict.get("workflow_stage") or "").strip().lower() or None,
        "operating_scenario": (rule_dict.get("operating_scenario") or "").strip() or None,
        "submission_method": (rule_dict.get("submission_method") or "").strip().lower() or None,
        "required_actions": _as_list(rule_dict.get("required_actions")),
        "required_forms": _as_list(rule_dict.get("required_forms")),
        "deadlines": _as_list(rule_dict.get("deadlines")),
        "source_id": source.id,
        "source_url": source.url,
        "source_document_name": source.name,
        "source_snippet": snippet[:2000] if snippet else None,
    }

    res, conflict = validation.assess_candidate(
        db, payload, raw_confidence=confidence_raw
    )
    if not res.valid:
        logger.info(
            "LLM rule rejected (validation): title=%r errors=%s",
            title[:80],
            res.errors,
        )
        return None
    if conflict.duplicate_of:
        # Don't store duplicates — caller can re-curate the existing rule.
        logger.info(
            "LLM rule skipped — duplicate of %s (title=%r)",
            conflict.duplicate_of,
            title[:80],
        )
        return None

    rule = models.Rule(
        tenant_id=source.tenant_id,
        state=payload["state"],
        tax_category=payload["tax_category"],
        rule_category=payload["rule_category"],
        rule_title=payload["rule_title"],
        rule_summary=payload["rule_summary"],
        detailed_rule=rule_dict.get("detailed_rule"),
        workflow_stage=payload["workflow_stage"],
        operating_scenario=payload["operating_scenario"],
        condition_logic=(rule_dict.get("condition_logic") or "").strip() or None,
        submission_method=payload["submission_method"],
        conditions=_as_list(rule_dict.get("conditions")),
        required_actions=payload["required_actions"],
        required_forms=payload["required_forms"],
        required_documentation=_as_list(rule_dict.get("required_documentation")),
        deadlines=payload["deadlines"],
        exceptions=_as_list(rule_dict.get("exceptions")),
        source_id=source.id,
        source_url=source.url,
        source_document_name=source.name,
        source_snippet=payload["source_snippet"],
        effective_date=rule_dict.get("effective_date"),
        effective_date_end=_effective_date_end(rule_dict),
        confidence_score=res.adjusted_confidence,
        review_status=res.suggested_review_status,
        extraction_method="llm",
        validation_errors=res.errors or None,
        validation_warnings=res.warnings or None,
        program_variant=_program_variant_for_rule(source, rule_dict),
        lineage={
            "extracted_from_chunk_ids": chunk_ids or [],
            "source_version_id": source_version_id,
            "source_checksum": source.checksum,
            "prompt_version": PROMPT_VERSION,
            "model": llm_client.model,
            "raw_confidence": confidence_raw,
            "conflicting_rule_ids": conflict.conflicting_rule_ids or None,
        },
    )
    db.add(rule)
    db.flush()
    sync_canonical_fields_for_new_rule(db, rule)
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
    source_version = versioning.latest_source_version(db, source.id)
    sv_id = source_version.id if source_version else None
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

        actions = _extract_actions(text)
        workflow_stage = _infer_workflow_stage(lowered)
        submission_method = _infer_submission_method(lowered)
        rule_category = _infer_rule_category(lowered)

        payload = {
            "tenant_id": source.tenant_id,
            "state": state_default,
            "tax_category": category,
            "rule_category": rule_category,
            "rule_title": title,
            "rule_summary": summary,
            "workflow_stage": workflow_stage,
            "submission_method": submission_method,
            "required_actions": actions,
            "required_forms": forms or None,
            "deadlines": deadlines or None,
            "source_id": source.id,
            "source_url": source.url,
            "source_document_name": source.name,
            "source_snippet": text[:1200],
        }
        res, conflict = validation.assess_candidate(
            db, payload, raw_confidence=0.45
        )
        if not res.valid or conflict.duplicate_of:
            continue

        rule = models.Rule(
            tenant_id=source.tenant_id,
            state=state_default,
            tax_category=category,
            rule_category=rule_category,
            rule_title=title,
            rule_summary=summary,
            detailed_rule=text[:2000],
            workflow_stage=workflow_stage,
            submission_method=submission_method,
            condition_logic=None,
            conditions=None,
            required_actions=actions,
            required_forms=forms or None,
            required_documentation=None,
            deadlines=deadlines or None,
            exceptions=None,
            source_id=source.id,
            source_url=source.url,
            source_document_name=source.name,
            source_snippet=text[:1200],
            confidence_score=res.adjusted_confidence,
            review_status=res.suggested_review_status,
            extraction_method="heuristic",
            validation_errors=res.errors or None,
            validation_warnings=res.warnings or None,
            program_variant=_program_variant_for_rule(source, {}),
            lineage={
                "extracted_from_chunk_ids": [chunk.id],
                "source_version_id": sv_id,
                "source_checksum": source.checksum,
                "prompt_version": PROMPT_VERSION,
                "model": "heuristic",
                "raw_confidence": 0.45,
                "conflicting_rule_ids": conflict.conflicting_rule_ids or None,
            },
        )
        db.add(rule)
        db.flush()
        sync_canonical_fields_for_new_rule(db, rule)
        created += 1

    db.flush()
    return created


def _infer_workflow_stage(text_lower: str) -> Optional[str]:
    if any(k in text_lower for k in ("register", "obtain a permit", "apply for")):
        return "intake"
    if any(k in text_lower for k in ("verify", "confirmation", "verified")):
        return "verification"
    if any(k in text_lower for k in ("documentation", "records", "keep records")):
        return "documentation"
    if any(k in text_lower for k in ("file", "remit", "submit", "pay", "payment")):
        return "submission"
    if any(k in text_lower for k in ("appeal", "protest", "resolution", "penalty")):
        return "resolution"
    return None


def _infer_submission_method(text_lower: str) -> Optional[str]:
    if any(k in text_lower for k in ("online", "e-file", "efile", "portal", "website")):
        return "online_portal"
    if "mail" in text_lower:
        return "mail"
    if any(k in text_lower for k in ("eft", "electronic funds", "ach")):
        return "eft"
    if "in person" in text_lower or "in-person" in text_lower:
        return "in_person"
    return None


def _infer_rule_category(text_lower: str) -> Optional[str]:
    if any(k in text_lower for k in ("register", "permit", "license")):
        return "registration"
    if any(k in text_lower for k in ("file", "return", "report")):
        return "filing"
    if any(k in text_lower for k in ("pay", "remit", "payment")):
        return "payment"
    if "exempt" in text_lower:
        return "exemption"
    if "threshold" in text_lower or "nexus" in text_lower:
        return "threshold"
    if "penalty" in text_lower or "fine" in text_lower:
        return "penalty"
    return None


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
