"""Answer-grounding + safety helpers.

Phase 6 of the upgrade plan. Three responsibilities:

1. Decide whether retrieved evidence is strong enough to attempt a real
   answer. If not, callers should return the canned "insufficient sources"
   response instead of letting the LLM speculate.
2. Scan an LLM-generated answer for fabricated specifics (forms, dollar
   thresholds, due-dates) that don't appear in any retrieved snippet, and
   surface a list of `safety_flags`.
3. Apply a conservative confidence penalty when fabrication is detected.

Everything here is heuristic — we treat the LLM as an untrusted output and
compare it against the retrieved context. The goal is not to silently
rewrite the LLM, only to flag and downgrade.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Optional

DISCLAIMER = (
    "_This is source-grounded operational guidance, not legal or tax "
    "advice. Always confirm against the cited official sources before "
    "acting._"
)

INSUFFICIENT_SOURCES_MESSAGE = (
    "I could not find sufficiently grounded source material to answer "
    "this confidently. Try ingesting an official state-tax URL or PDF "
    "covering this topic, then re-run the question."
)

# Minimum lexical+vector top score we require before letting the LLM
# answer at all. Below this we return the canned message so we never put
# words in the LLM's mouth from near-empty context.
MIN_TOP_SCORE = 0.05
MIN_RULES_OR_CHUNKS = 1


# ---------------------------------------------------------------------------
# Patterns used for fabrication detection
# ---------------------------------------------------------------------------


# Forms: things like "Form 1040", "Form CDTFA-401", "Form NYS-45", "DR-1".
_FORM_RE = re.compile(
    r"\b(?:Form\s+|form\s+)?([A-Z]{2,8}-\d{1,5}[A-Z]?|\d{3,5}[A-Z]?)\b"
)
# Dollar thresholds.
_DOLLAR_RE = re.compile(r"\$\s?[\d,]{3,}(?:\.\d+)?")
# Percentages used as tax rates / penalties.
_PERCENT_RE = re.compile(r"\b\d{1,3}(?:\.\d+)?\s?%")
# Specific calendar dates ("April 15", "January 31, 2025").
_DATE_RE = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{1,2}(?:,\s*\d{4})?\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class EvidenceVerdict:
    sufficient: bool = True
    reason: str = ""
    top_score: float = 0.0
    n_rules: int = 0
    n_chunks: int = 0


@dataclass
class SafetyVerdict:
    flags: list[str] = field(default_factory=list)
    fabricated_forms: list[str] = field(default_factory=list)
    fabricated_dollars: list[str] = field(default_factory=list)
    fabricated_percents: list[str] = field(default_factory=list)
    fabricated_dates: list[str] = field(default_factory=list)
    confidence_penalty: float = 0.0

    @property
    def has_fabrication(self) -> bool:
        return bool(
            self.fabricated_forms
            or self.fabricated_dollars
            or self.fabricated_percents
            or self.fabricated_dates
        )


# ---------------------------------------------------------------------------
# Evidence sufficiency
# ---------------------------------------------------------------------------


def assess_evidence(
    rules: list,
    chunks: list,
) -> EvidenceVerdict:
    """Inspect retrieved rules + chunks and decide if we have enough to
    answer at all. The actual list types are `RetrievedRule` / `RetrievedChunk`
    but we only rely on the `.score` attribute so importing the dataclass
    is unnecessary.
    """
    n_rules = len(rules)
    n_chunks = len(chunks)
    top = 0.0
    if rules:
        top = max(top, max(getattr(r, "score", 0.0) for r in rules))
    if chunks:
        top = max(top, max(getattr(c, "score", 0.0) for c in chunks))

    if (n_rules + n_chunks) < MIN_RULES_OR_CHUNKS:
        return EvidenceVerdict(
            sufficient=False,
            reason="no rules or chunks retrieved",
            top_score=top,
            n_rules=n_rules,
            n_chunks=n_chunks,
        )
    if top < MIN_TOP_SCORE:
        return EvidenceVerdict(
            sufficient=False,
            reason=f"top retrieval score {top:.3f} below threshold {MIN_TOP_SCORE}",
            top_score=top,
            n_rules=n_rules,
            n_chunks=n_chunks,
        )
    return EvidenceVerdict(
        sufficient=True,
        reason="ok",
        top_score=top,
        n_rules=n_rules,
        n_chunks=n_chunks,
    )


# ---------------------------------------------------------------------------
# Fabrication detection
# ---------------------------------------------------------------------------


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def _haystack_from_context(*texts: Iterable[Optional[str]]) -> str:
    parts: list[str] = []
    for group in texts:
        for t in group or []:
            if t:
                parts.append(t)
    return _norm(" \n".join(parts))


def detect_fabrications(
    answer_text: str,
    *,
    rule_snippets: Iterable[str] = (),
    rule_form_lists: Iterable[Iterable[str]] = (),
    chunk_texts: Iterable[str] = (),
    rule_titles: Iterable[str] = (),
    rule_summaries: Iterable[str] = (),
) -> SafetyVerdict:
    """Compare specifics in `answer_text` against retrieved context.

    Anything in the answer that looks like a Form id / dollar amount /
    percent / date but isn't anywhere in the retrieved snippets is
    flagged as a likely fabrication. This is intentionally conservative
    — false positives are preferable to silent fabrication.
    """
    verdict = SafetyVerdict()
    if not answer_text:
        return verdict

    haystack = _haystack_from_context(
        rule_snippets, chunk_texts, rule_titles, rule_summaries
    )
    # Flatten declared forms list into the haystack too.
    extra_forms: list[str] = []
    for forms in rule_form_lists:
        for f in forms or []:
            if f:
                extra_forms.append(_norm(f))
    haystack = haystack + " " + " ".join(extra_forms)

    lower_answer = _norm(answer_text)

    # ---- Forms ----
    seen_forms: set[str] = set()
    for m in _FORM_RE.finditer(answer_text):
        form_id = m.group(1)
        # Skip pure-numeric matches that look like years or counts unless
        # they appear with the explicit "Form" prefix nearby.
        snippet_pre = answer_text[max(0, m.start() - 6) : m.start()].lower()
        if form_id.isdigit() and "form" not in snippet_pre:
            continue
        norm_form = _norm(form_id)
        if norm_form in seen_forms:
            continue
        seen_forms.add(norm_form)
        if norm_form not in haystack and f"form {norm_form}" not in haystack:
            verdict.fabricated_forms.append(form_id)

    # ---- Dollars ----
    for m in _DOLLAR_RE.findall(answer_text):
        norm_d = _norm(m)
        if norm_d not in haystack:
            verdict.fabricated_dollars.append(m.strip())

    # ---- Percents ----
    for m in _PERCENT_RE.findall(answer_text):
        norm_p = _norm(m)
        if norm_p not in haystack:
            verdict.fabricated_percents.append(m.strip())

    # ---- Specific dates ----
    for m in _DATE_RE.findall(answer_text):
        if _norm(m) not in haystack:
            verdict.fabricated_dates.append(m.strip())

    # Dedupe.
    verdict.fabricated_forms = sorted(set(verdict.fabricated_forms))
    verdict.fabricated_dollars = sorted(set(verdict.fabricated_dollars))
    verdict.fabricated_percents = sorted(set(verdict.fabricated_percents))
    verdict.fabricated_dates = sorted(set(verdict.fabricated_dates))

    if verdict.fabricated_forms:
        verdict.flags.append(
            f"forms not present in sources: {', '.join(verdict.fabricated_forms)}"
        )
    if verdict.fabricated_dollars:
        verdict.flags.append(
            f"dollar amounts not present in sources: {', '.join(verdict.fabricated_dollars)}"
        )
    if verdict.fabricated_percents:
        verdict.flags.append(
            f"percentages not present in sources: {', '.join(verdict.fabricated_percents)}"
        )
    if verdict.fabricated_dates:
        verdict.flags.append(
            f"dates not present in sources: {', '.join(verdict.fabricated_dates)}"
        )

    # Confidence penalty: 5pp per category with a fabrication, capped at 25pp.
    penalty = 0.0
    if verdict.fabricated_forms:
        penalty += 0.10
    if verdict.fabricated_dollars:
        penalty += 0.10
    if verdict.fabricated_percents:
        penalty += 0.05
    if verdict.fabricated_dates:
        penalty += 0.05
    verdict.confidence_penalty = min(penalty, 0.25)
    return verdict


def append_disclaimer(answer_text: str) -> str:
    """Add the standardised disclaimer if it isn't already present."""
    answer_text = (answer_text or "").rstrip()
    if "not legal or tax advice" in answer_text.lower():
        return answer_text
    if not answer_text:
        return DISCLAIMER
    return answer_text + "\n\n" + DISCLAIMER


def insufficient_answer(state: Optional[str], tax_category: Optional[str]) -> str:
    """Canned message used when evidence is too thin to attempt an answer."""
    scope_parts = []
    if state:
        scope_parts.append(f"state **{state}**")
    if tax_category:
        scope_parts.append(f"category **{tax_category.replace('_', ' ')}**")
    scope = " and ".join(scope_parts)
    msg = INSUFFICIENT_SOURCES_MESSAGE
    if scope:
        msg += f"\n\nFilters applied: {scope}."
    return append_disclaimer(msg)
