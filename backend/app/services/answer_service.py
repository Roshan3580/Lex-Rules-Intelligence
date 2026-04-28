"""Answer service: question -> grounded answer.

Phase 6 hardening:

- Evidence sufficiency is checked before generation. If retrieval came
  back empty or near-empty we return the canned "insufficient sources"
  response instead of letting the LLM speculate.
- LLM prompt is tightened to forbid invented forms/deadlines/$/% and to
  emit a structured answer with the brief's required sections.
- Generated answers are scanned for fabricated specifics; flagged items
  are surfaced as `safety_flags` and the confidence is downgraded.
- Every successful answer ends with a standard disclaimer.
- Audit metadata (`chunks_used`, `source_versions_used`, `retrieval_mode`,
  `safety_flags`) is persisted on the `Answer` row so the entire grounding
  chain is reconstructable later.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from .. import models, schemas
from ..utils.llm_client import llm_client
from . import answer_safety, retrieval_service, versioning

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You are a US state tax research assistant. You ONLY answer using the "
    "provided context. If the context does not state something, say so "
    "explicitly — never invent forms, due dates, dollar thresholds, "
    "percentages, or rule numbers. Cite each non-trivial claim by its [n] "
    "context index. Use the structured sections requested by the user."
)


def answer_question(
    db: Session,
    *,
    question: str,
    state: Optional[str] = None,
    tax_category: Optional[str] = None,
    workflow_stage: Optional[str] = None,
    operating_scenario: Optional[str] = None,
    top_k: int = 6,
    statuses: Optional[list[str]] = None,
) -> schemas.AnswerOut:
    q_row = models.Question(
        text=question, state=state, tax_category=tax_category
    )
    db.add(q_row)
    db.flush()

    retrieved_rules = retrieval_service.retrieve_rules(
        db,
        question,
        state=state,
        tax_category=tax_category,
        workflow_stage=workflow_stage,
        operating_scenario=operating_scenario,
        statuses=statuses,
        top_k=top_k,
    )
    retrieved_chunks = retrieval_service.retrieve_chunks(
        db, question, state=state, tax_category=tax_category, top_k=top_k
    )
    retrieval_mode = retrieval_service.last_mode()

    citations = _build_citations(retrieved_rules, retrieved_chunks)
    safety_flags: list[str] = []

    # ---- Evidence gate ----
    verdict = answer_safety.assess_evidence(retrieved_rules, retrieved_chunks)
    if not verdict.sufficient:
        ans = answer_safety.insufficient_answer(state, tax_category)
        method = "fallback"
        confidence = 0.0
        safety_flags.append(f"insufficient_evidence: {verdict.reason}")
    elif llm_client.enabled:
        try:
            ans, confidence, llm_flags = _llm_answer(
                question,
                state,
                tax_category,
                workflow_stage,
                operating_scenario,
                retrieved_rules,
                retrieved_chunks,
            )
            method = "llm"
            safety_flags.extend(llm_flags)
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
    chunks_used_ids = [c.chunk.id for c in retrieved_chunks]
    source_ids = {r.rule.source_id for r in retrieved_rules if r.rule.source_id}
    source_ids.update(c.source.id for c in retrieved_chunks if c.source)
    source_version_ids = _latest_source_versions(db, source_ids)

    answer_row = models.Answer(
        question_id=q_row.id,
        answer_text=ans,
        confidence_score=confidence,
        citations=[c.model_dump() for c in citations],
        rules_used=[r.id for r in rules_used],
        chunks_used=chunks_used_ids,
        source_versions_used=source_version_ids,
        retrieval_mode=retrieval_mode,
        safety_flags=safety_flags or None,
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
        chunks_used=chunks_used_ids,
        source_versions_used=source_version_ids,
        safety_flags=safety_flags,
        method=method,
        retrieval_mode=retrieval_mode,
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


def _latest_source_versions(db: Session, source_ids) -> list[str]:
    out: list[str] = []
    for sid in sorted({s for s in source_ids if s}):
        sv = versioning.latest_source_version(db, sid)
        if sv is not None:
            out.append(sv.id)
    return out


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
            f"Documents: {', '.join(rule.required_documentation or []) or 'n/a'}\n"
            f"Deadlines: {', '.join(rule.deadlines or []) or 'n/a'}\n"
            f"Actions: {', '.join(rule.required_actions or []) or 'n/a'}\n"
            f"Exceptions: {', '.join(rule.exceptions or []) or 'n/a'}\n"
            f"Effective date: {rule.effective_date or 'n/a'}\n"
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
    workflow_stage: Optional[str],
    operating_scenario: Optional[str],
    retrieved_rules: list[retrieval_service.RetrievedRule],
    retrieved_chunks: list[retrieval_service.RetrievedChunk],
) -> tuple[str, float, list[str]]:
    """Returns (answer_markdown, confidence, safety_flags)."""
    context = _format_context(retrieved_rules, retrieved_chunks)
    user = (
        f"Question: {question}\n"
        f"State filter: {state or 'any'}\n"
        f"Tax category filter: {tax_category or 'any'}\n"
        f"Workflow stage filter: {workflow_stage or 'any'}\n"
        f"Operating scenario: {operating_scenario or 'any'}\n\n"
        f"Context:\n{context}\n\n"
        "Respond as JSON with this exact shape:\n"
        '{"answer": "<markdown answer>", '
        '"confidence": <0..1>, '
        '"missing_info": "<what is unclear or absent, if any>"}\n\n'
        "The markdown answer MUST contain these sections (omit a section "
        "only if the context says nothing relevant):\n"
        "  ### Direct answer\n"
        "  ### Applicable conditions\n"
        "  ### Required actions\n"
        "  ### Required forms / documents\n"
        "  ### Deadlines / effective dates\n"
        "  ### Exceptions\n"
        "  ### Sources\n"
        "Use [n] inline citations referencing the context indices. Never "
        "invent forms, dollar thresholds, percentages, or specific dates "
        "that are not in the context. If the context is unclear on a "
        "section, write 'Not stated in indexed sources.' for that section."
    )
    data = llm_client.chat_json(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
        max_tokens=1100,
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

    if not answer_text:
        return (
            answer_safety.insufficient_answer(state, tax_category),
            0.0,
            ["llm_returned_empty"],
        )

    # ---- Fabrication scan ----
    safety = answer_safety.detect_fabrications(
        answer_text,
        rule_snippets=[r.rule.source_snippet or "" for r in retrieved_rules],
        rule_form_lists=[r.rule.required_forms or [] for r in retrieved_rules],
        chunk_texts=[c.chunk.text for c in retrieved_chunks],
        rule_titles=[r.rule.rule_title for r in retrieved_rules],
        rule_summaries=[r.rule.rule_summary for r in retrieved_rules],
    )
    if safety.has_fabrication:
        confidence = max(0.0, confidence - safety.confidence_penalty)
        warning = (
            "\n\n> ⚠️ Potential fabrication detected — the items below appear in "
            "the generated answer but were not found in the cited sources. "
            "Verify before relying on them: "
            + "; ".join(safety.flags)
        )
        answer_text += warning

    answer_text = answer_safety.append_disclaimer(answer_text)
    return answer_text, round(confidence, 4), safety.flags


# ---------------------------------------------------------------------------
# Deterministic fallback (structured)
# ---------------------------------------------------------------------------


def _fallback_answer(
    question: str,
    state: Optional[str],
    tax_category: Optional[str],
    retrieved_rules: list[retrieval_service.RetrievedRule],
    retrieved_chunks: list[retrieval_service.RetrievedChunk],
) -> tuple[str, float]:
    if not retrieved_rules and not retrieved_chunks:
        return answer_safety.insufficient_answer(state, tax_category), 0.0

    rules = [r.rule for r in retrieved_rules[:5]]
    actions: list[str] = []
    forms: list[str] = []
    docs: list[str] = []
    deadlines: list[str] = []
    exceptions: list[str] = []
    conditions: list[str] = []
    effective_dates: list[str] = []
    last_checked: list[str] = []
    citations_block: list[str] = []

    for i, rule in enumerate(rules, start=1):
        for a in rule.required_actions or []:
            actions.append(f"{a} [{i}]")
        for f in rule.required_forms or []:
            forms.append(f"{f} [{i}]")
        for d in rule.required_documentation or []:
            docs.append(f"{d} [{i}]")
        for d in rule.deadlines or []:
            deadlines.append(f"{d} [{i}]")
        for e in rule.exceptions or []:
            exceptions.append(f"{e} [{i}]")
        for c in rule.conditions or []:
            conditions.append(f"{c} [{i}]")
        if rule.effective_date:
            effective_dates.append(f"{rule.effective_date} [{i}]")
        if getattr(rule, "source", None) and rule.source.last_checked:
            last_checked.append(rule.source.last_checked.isoformat())
        cite_label = rule.source_document_name or rule.source_url or "Source"
        if rule.source_url:
            citations_block.append(f"- [{i}] [{cite_label}]({rule.source_url})")
        else:
            citations_block.append(f"- [{i}] {cite_label}")

    for j, c in enumerate(retrieved_chunks[: max(0, 8 - len(rules))], start=len(rules) + 1):
        cite_label = c.source.name or c.source.url or "Source"
        if c.source.url:
            citations_block.append(f"- [{j}] [{cite_label}]({c.source.url})")
        else:
            citations_block.append(f"- [{j}] {cite_label}")
        if c.source.last_checked:
            last_checked.append(c.source.last_checked.isoformat())

    parts: list[str] = []

    header = "### Direct answer\nBased on the indexed sources"
    if state:
        header += f" for **{state}**"
    if tax_category:
        header += f" in the **{tax_category.replace('_', ' ')}** category"
    header += ":\n"
    if rules:
        for i, rule in enumerate(rules, start=1):
            header += f"- **[{i}] {rule.rule_title}** — {rule.rule_summary}\n"
    else:
        header += "_The retrieved chunks below are the most relevant text we found._"
    parts.append(header.rstrip())

    parts.append(
        "### Applicable conditions\n"
        + ("\n".join(f"- {x}" for x in conditions) if conditions else "Not stated in indexed sources.")
    )
    parts.append(
        "### Required actions\n"
        + ("\n".join(f"- {x}" for x in actions) if actions else "Not stated in indexed sources.")
    )

    forms_doc_block = []
    if forms:
        forms_doc_block.append("**Forms:**\n" + "\n".join(f"- {x}" for x in forms))
    if docs:
        forms_doc_block.append("**Documents:**\n" + "\n".join(f"- {x}" for x in docs))
    parts.append(
        "### Required forms / documents\n"
        + ("\n\n".join(forms_doc_block) if forms_doc_block else "Not stated in indexed sources.")
    )

    deadline_block = []
    if deadlines:
        deadline_block.append("**Deadlines:**\n" + "\n".join(f"- {x}" for x in deadlines))
    if effective_dates:
        deadline_block.append("**Effective dates:**\n" + "\n".join(f"- {x}" for x in effective_dates))
    parts.append(
        "### Deadlines / effective dates\n"
        + ("\n\n".join(deadline_block) if deadline_block else "Not stated in indexed sources.")
    )

    parts.append(
        "### Exceptions\n"
        + ("\n".join(f"- {x}" for x in exceptions) if exceptions else "Not stated in indexed sources.")
    )

    if last_checked:
        parts.append(f"_Sources last checked: {min(last_checked)} (oldest)._")

    parts.append("### Sources\n" + ("\n".join(citations_block) if citations_block else "n/a"))

    parts.append(
        "_This response was generated without a connected LLM. "
        "It summarises only what the retrieved rules and source chunks "
        "explicitly say._"
    )

    confidence = min(0.7, 0.35 + 0.07 * len(rules))
    return answer_safety.append_disclaimer("\n\n".join(parts)), round(confidence, 4)
