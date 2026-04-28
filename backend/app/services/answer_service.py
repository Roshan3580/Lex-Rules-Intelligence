"""Answer service: question -> grounded answer.

Flow (RAG-style):
  1. Persist the question.
  2. Retrieve relevant rules + chunks (filtered by state/category).
  3. If LLM is configured, ask it to answer GROUNDED IN the retrieved
     context (no outside knowledge), and return JSON with citations and
     confidence.
  4. If LLM is not configured, synthesize a deterministic answer from the
     retrieved rules so the prototype is fully usable offline.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from .. import models, schemas
from ..utils.llm_client import llm_client
from . import retrieval_service

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You are a US state tax research assistant. Answer the user's question "
    "using ONLY the provided context. If the context does not contain "
    "enough information to answer, say so clearly and recommend checking "
    "the cited source. Do not invent forms, deadlines, dollar thresholds, "
    "or rule numbers. Always reference your sources by their [n] index."
)


def answer_question(
    db: Session,
    *,
    question: str,
    state: Optional[str] = None,
    tax_category: Optional[str] = None,
    top_k: int = 6,
) -> schemas.AnswerOut:
    q_row = models.Question(
        text=question, state=state, tax_category=tax_category
    )
    db.add(q_row)
    db.flush()

    retrieved_rules = retrieval_service.retrieve_rules(
        db, question, state=state, tax_category=tax_category, top_k=top_k
    )
    retrieved_chunks = retrieval_service.retrieve_chunks(
        db, question, state=state, tax_category=tax_category, top_k=top_k
    )

    citations = _build_citations(retrieved_rules, retrieved_chunks)

    if not retrieved_rules and not retrieved_chunks:
        ans = _no_context_answer(question, state, tax_category)
        method = "fallback"
        confidence = 0.0
    elif llm_client.enabled:
        try:
            ans, confidence = _llm_answer(
                question, state, tax_category, retrieved_rules, retrieved_chunks
            )
            method = "llm"
        except Exception as exc:
            logger.warning("LLM answer failed, falling back: %s", exc)
            ans, confidence = _fallback_answer(
                question, state, tax_category, retrieved_rules, retrieved_chunks
            )
            method = "fallback"
    else:
        ans, confidence = _fallback_answer(
            question, state, tax_category, retrieved_rules, retrieved_chunks
        )
        method = "fallback"

    rules_used = [r.rule for r in retrieved_rules]

    answer_row = models.Answer(
        question_id=q_row.id,
        answer_text=ans,
        confidence_score=confidence,
        citations=[c.model_dump() for c in citations],
        rules_used=[r.id for r in rules_used],
        method=method,
    )
    db.add(answer_row)
    db.commit()
    db.refresh(answer_row)

    return schemas.AnswerOut(
        id=answer_row.id,
        question_id=q_row.id,
        question=question,
        answer=ans,
        confidence_score=confidence,
        citations=citations,
        rules_used=[schemas.RuleOut.model_validate(r) for r in rules_used],
        method=method,
        state=state,
        tax_category=tax_category,
        created_at=answer_row.created_at,
    )


# ---------------------------------------------------------------------------
# Citation construction
# ---------------------------------------------------------------------------


def _build_citations(
    retrieved_rules: list[retrieval_service.RetrievedRule],
    retrieved_chunks: list[retrieval_service.RetrievedChunk],
) -> list[schemas.Citation]:
    citations: list[schemas.Citation] = []
    seen: set[tuple[Optional[str], Optional[str]]] = set()

    for r in retrieved_rules:
        rule = r.rule
        key = (rule.id, None)
        if key in seen:
            continue
        seen.add(key)
        snippet = (rule.source_snippet or rule.rule_summary or "")[:600]
        citations.append(
            schemas.Citation(
                rule_id=rule.id,
                source_id=rule.source_id,
                source_name=rule.source_document_name,
                source_url=rule.source_url,
                snippet=snippet,
                state=rule.state,
                tax_category=rule.tax_category,
                relevance=round(r.score, 4),
            )
        )

    for c in retrieved_chunks:
        key = (None, c.chunk.id)
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            schemas.Citation(
                rule_id=None,
                source_id=c.source.id,
                source_name=c.source.name,
                source_url=c.source.url,
                snippet=c.chunk.text[:600],
                state=c.source.state,
                tax_category=c.source.tax_category,
                relevance=round(c.score, 4),
            )
        )

    return citations[:10]


# ---------------------------------------------------------------------------
# LLM answer
# ---------------------------------------------------------------------------


def _format_context(
    retrieved_rules: list[retrieval_service.RetrievedRule],
    retrieved_chunks: list[retrieval_service.RetrievedChunk],
) -> str:
    parts: list[str] = []
    idx = 1
    for r in retrieved_rules[:6]:
        rule = r.rule
        parts.append(
            f"[{idx}] (rule, {rule.state} / {rule.tax_category})\n"
            f"Title: {rule.rule_title}\n"
            f"Summary: {rule.rule_summary}\n"
            f"Forms: {', '.join(rule.required_forms or []) or 'n/a'}\n"
            f"Deadlines: {', '.join(rule.deadlines or []) or 'n/a'}\n"
            f"Actions: {', '.join(rule.required_actions or []) or 'n/a'}\n"
            f"Source: {rule.source_document_name or rule.source_url or 'unknown'}"
        )
        idx += 1
    for c in retrieved_chunks[:4]:
        parts.append(
            f"[{idx}] (snippet, {c.source.state or '-'} / "
            f"{c.source.tax_category or '-'})\n{c.chunk.text[:800]}\n"
            f"Source: {c.source.name}"
        )
        idx += 1
    return "\n\n".join(parts)


def _llm_answer(
    question: str,
    state: Optional[str],
    tax_category: Optional[str],
    retrieved_rules: list[retrieval_service.RetrievedRule],
    retrieved_chunks: list[retrieval_service.RetrievedChunk],
) -> tuple[str, float]:
    context = _format_context(retrieved_rules, retrieved_chunks)
    user = (
        f"Question: {question}\n"
        f"State filter: {state or 'any'}\n"
        f"Category filter: {tax_category or 'any'}\n\n"
        f"Context:\n{context}\n\n"
        "Respond as JSON with this exact shape:\n"
        '{"answer": "<markdown answer with [n] citations>", '
        '"confidence": <0..1>, '
        '"missing_info": "<what is unclear or absent, if any>"}'
    )
    data = llm_client.chat_json(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
        max_tokens=900,
    )

    if not isinstance(data, dict):
        raise RuntimeError("LLM returned non-object answer payload")

    answer_text = (data.get("answer") or "").strip()
    try:
        confidence = float(data.get("confidence") or 0.6)
    except (TypeError, ValueError):
        confidence = 0.6
    confidence = max(0.0, min(confidence, 1.0))

    missing = (data.get("missing_info") or "").strip()
    if missing:
        answer_text += f"\n\n**Missing or unclear:** {missing}"

    return answer_text or _stringify_no_answer(question, state, tax_category), confidence


# ---------------------------------------------------------------------------
# Deterministic fallback
# ---------------------------------------------------------------------------


def _fallback_answer(
    question: str,
    state: Optional[str],
    tax_category: Optional[str],
    retrieved_rules: list[retrieval_service.RetrievedRule],
    retrieved_chunks: list[retrieval_service.RetrievedChunk],
) -> tuple[str, float]:
    if not retrieved_rules and not retrieved_chunks:
        return _no_context_answer(question, state, tax_category), 0.0

    bullets: list[str] = []
    forms: set[str] = set()
    deadlines: set[str] = set()
    actions: set[str] = set()

    for i, r in enumerate(retrieved_rules[:5], start=1):
        rule = r.rule
        for f in rule.required_forms or []:
            forms.add(f)
        for d in rule.deadlines or []:
            deadlines.add(d)
        for a in rule.required_actions or []:
            actions.add(a)
        bullets.append(
            f"- **[{i}] {rule.rule_title}** "
            f"({rule.state} · {rule.tax_category.replace('_', ' ')}): "
            f"{rule.rule_summary}"
        )

    parts: list[str] = []
    header = "Based on the indexed sources"
    if state:
        header += f" for **{state}**"
    if tax_category:
        header += f" in the **{tax_category.replace('_', ' ')}** category"
    header += ", here is what we found:"
    parts.append(header)

    if bullets:
        parts.append("\n".join(bullets))

    if forms:
        parts.append("**Forms referenced:** " + ", ".join(sorted(forms)))
    if deadlines:
        parts.append("**Deadlines referenced:** " + ", ".join(sorted(deadlines)))
    if actions:
        compact = "; ".join(list(sorted(actions))[:6])
        parts.append("**Required actions:** " + compact)

    parts.append(
        "_This response was generated without a connected LLM. It "
        "summarizes the highest-ranked rules and source snippets for "
        "your filters; check the citations panel for verbatim source text._"
    )

    confidence = min(0.7, 0.35 + 0.1 * len(retrieved_rules[:5]))
    return "\n\n".join(parts), confidence


def _no_context_answer(
    question: str, state: Optional[str], tax_category: Optional[str]
) -> str:
    fragments = []
    if state:
        fragments.append(f"state **{state}**")
    if tax_category:
        fragments.append(f"category **{tax_category.replace('_', ' ')}**")
    scope = " and ".join(fragments) or "your selected filters"
    return (
        f"We don't yet have indexed source material that covers {scope} "
        f"for this question. Try uploading a relevant PDF, ingesting a "
        f"state-government URL, or removing the filters to broaden the "
        f"search. The system will not guess when sources are missing."
    )


def _stringify_no_answer(
    question: str, state: Optional[str], tax_category: Optional[str]
) -> str:
    return _no_context_answer(question, state, tax_category)
