"""Retrieval service.

Phase 5 hybrid retrieval. Three retrieval modes are supported:

- `lexical` — TF-style scoring (works without numpy or embeddings).
- `vector`  — cosine similarity from the in-memory vector index.
- `hybrid`  — both, fused as
        score = α * lexical + β * vector + γ * confidence + δ * freshness
              + ε * published_boost
  Filtering by state / tax_category / workflow_stage / review_status happens
  *before* ranking so we never rank irrelevant rules into the top-k.

The retrieval mode actually used is reported back via `last_mode()` so
upstream answer-generation can stamp it on the response payload.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from .. import models
from .embeddings import embedder
from .vector_store import vector_store

_STOPWORDS = {
    "the", "a", "an", "is", "are", "of", "to", "in", "on", "for", "and",
    "or", "by", "with", "what", "how", "do", "does", "i", "we", "you",
    "be", "this", "that", "it", "as", "at", "from", "if", "any", "must",
    "rules", "rule", "tax", "taxes", "state", "law", "laws",
}

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "") if t.lower() not in _STOPWORDS]


def _score(query_tokens: list[str], doc_text: str) -> float:
    if not query_tokens or not doc_text:
        return 0.0
    doc_tokens = _tokenize(doc_text)
    if not doc_tokens:
        return 0.0
    counts = Counter(doc_tokens)
    total = len(doc_tokens)
    score = 0.0
    for q in query_tokens:
        if q in counts:
            tf = counts[q] / total
            # Slight bias toward longer, more specific terms.
            score += tf * (1.0 + math.log(1 + len(q)))
    return score


@dataclass
class RetrievedRule:
    rule: models.Rule
    score: float
    lexical_score: float = 0.0
    vector_score: float = 0.0


@dataclass
class RetrievedChunk:
    chunk: models.SourceChunk
    source: models.Source
    score: float
    lexical_score: float = 0.0
    vector_score: float = 0.0


# ---------------------------------------------------------------------------
# Mode selection + signal helpers
# ---------------------------------------------------------------------------


_LAST_MODE: dict[str, str] = {"value": "lexical"}


def last_mode() -> str:
    return _LAST_MODE["value"]


def _set_mode(mode: str) -> None:
    _LAST_MODE["value"] = mode


def _resolve_mode(prefer_hybrid: bool = True) -> str:
    if prefer_hybrid and embedder.enabled:
        stats = vector_store.stats()
        if stats.get("enabled") and (stats.get("size") or 0) > 0:
            return "hybrid"
    return "lexical"


def _freshness_boost(when: Optional[datetime]) -> float:
    if when is None:
        return 0.0
    age_days = max(0.0, (datetime.utcnow() - when).total_seconds() / 86400.0)
    # 1.0 fresh today, decaying to ~0.3 after a year, ~0 after 5 years.
    return max(0.0, math.exp(-age_days / 180.0))


def _published_boost(review_status: str) -> float:
    if review_status == "published":
        return 0.25
    if review_status == "approved":
        return 0.15
    if review_status == "auto_validated":
        return 0.05
    return 0.0


def _confidence_boost(confidence: float) -> float:
    return 0.10 * float(confidence or 0.0)


def _normalize(values: list[float]) -> list[float]:
    """Min-max to [0,1] so lexical and vector scores are comparable."""
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if hi - lo < 1e-9:
        return [0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


# Hybrid score weights. Tuned conservatively so lexical and vector signals
# both contribute even at low magnitudes; metadata boosts (confidence,
# freshness, published) act as tie-breakers rather than dominators.
_W_LEXICAL = 0.45
_W_VECTOR = 0.45
_W_CONFIDENCE = 0.10  # rule-only
_W_FRESHNESS = 0.05
_W_PUBLISHED = 0.10  # rule-only


def retrieve_rules(
    db: Session,
    query: str,
    *,
    state: Optional[str] = None,
    tax_category: Optional[str] = None,
    workflow_stage: Optional[str] = None,
    operating_scenario: Optional[str] = None,
    top_k: int = 6,
    statuses: Optional[list[str]] = None,
    prefer_hybrid: bool = True,
) -> list[RetrievedRule]:
    """Return the top-k rules for a query, filtered then ranked.

    Filtering happens first (state, tax_category, workflow_stage,
    review_status); ranking blends lexical and (when available) vector
    signals plus confidence/freshness/published boosts.
    """
    q = db.query(models.Rule)
    if state:
        q = q.filter(models.Rule.state == state)
    if tax_category:
        q = q.filter(models.Rule.tax_category == tax_category)
    if workflow_stage:
        q = q.filter(models.Rule.workflow_stage == workflow_stage)
    if statuses:
        q = q.filter(models.Rule.review_status.in_(statuses))
    rules = q.all()
    if not rules:
        return []

    tokens = _tokenize(query)
    op_scenario_tokens = _tokenize(operating_scenario or "")

    # Lexical signal
    lexical_scores: list[float] = []
    for r in rules:
        haystack = " ".join(
            filter(
                None,
                [
                    r.rule_title,
                    r.rule_summary,
                    r.detailed_rule or "",
                    r.operating_scenario or "",
                    r.condition_logic or "",
                    " ".join(r.required_actions or []),
                    " ".join(r.required_forms or []),
                    " ".join(r.required_documentation or []),
                    " ".join(r.deadlines or []),
                    " ".join(r.conditions or []),
                    " ".join(r.exceptions or []),
                    r.source_snippet or "",
                ],
            )
        )
        s = _score(tokens, haystack)
        if op_scenario_tokens:
            s += 0.5 * _score(op_scenario_tokens, haystack)
        lexical_scores.append(s)

    # Vector signal (chunk → rule via source_id mapping)
    mode = _resolve_mode(prefer_hybrid)
    _set_mode(mode)
    vector_scores = [0.0] * len(rules)
    if mode == "hybrid":
        rule_source_to_idx: dict[str, list[int]] = {}
        for i, r in enumerate(rules):
            if r.source_id:
                rule_source_to_idx.setdefault(r.source_id, []).append(i)
        matches = vector_store.query(
            query,
            state=state,
            tax_category=tax_category,
            top_k=max(top_k * 4, 24),
        )
        per_source_max: dict[str, float] = {}
        for m in matches:
            cur = per_source_max.get(m.source_id, 0.0)
            if m.score > cur:
                per_source_max[m.source_id] = m.score
        for sid, score in per_source_max.items():
            for idx in rule_source_to_idx.get(sid, []):
                if score > vector_scores[idx]:
                    vector_scores[idx] = score

    lex_norm = _normalize(lexical_scores)
    vec_norm = _normalize(vector_scores) if mode == "hybrid" else [0.0] * len(rules)

    scored: list[RetrievedRule] = []
    for r, lex_raw, vec_raw, lex_n, vec_n in zip(
        rules, lexical_scores, vector_scores, lex_norm, vec_norm
    ):
        if lex_raw <= 0 and vec_raw <= 0:
            continue
        s = (
            _W_LEXICAL * lex_n
            + (_W_VECTOR * vec_n if mode == "hybrid" else 0.0)
            + _W_CONFIDENCE * _confidence_boost(r.confidence_score)
            + _W_FRESHNESS * _freshness_boost(r.updated_at)
            + _W_PUBLISHED * _published_boost(r.review_status)
        )
        scored.append(
            RetrievedRule(
                rule=r,
                score=round(s, 6),
                lexical_score=round(lex_raw, 6),
                vector_score=round(vec_raw, 6),
            )
        )

    scored.sort(key=lambda x: x.score, reverse=True)
    return scored[:top_k]


def retrieve_chunks(
    db: Session,
    query: str,
    *,
    state: Optional[str] = None,
    tax_category: Optional[str] = None,
    top_k: int = 6,
    prefer_hybrid: bool = True,
) -> list[RetrievedChunk]:
    """Return the top-k source chunks for a query (hybrid when available)."""
    q = db.query(models.SourceChunk).join(models.Source)
    if state:
        q = q.filter(
            (models.SourceChunk.state == state) | (models.Source.state == state)
        )
    if tax_category:
        q = q.filter(
            (models.SourceChunk.tax_category == tax_category)
            | (models.Source.tax_category == tax_category)
        )
    chunks = q.all()
    if not chunks:
        return []

    tokens = _tokenize(query)
    lexical_scores = [_score(tokens, c.text) for c in chunks]

    mode = _resolve_mode(prefer_hybrid)
    _set_mode(mode)

    vector_by_id: dict[str, float] = {}
    if mode == "hybrid":
        matches = vector_store.query(
            query,
            state=state,
            tax_category=tax_category,
            top_k=max(top_k * 4, 24),
        )
        for m in matches:
            vector_by_id[m.chunk_id] = m.score

    vector_scores = [vector_by_id.get(c.id, 0.0) for c in chunks]
    lex_norm = _normalize(lexical_scores)
    vec_norm = _normalize(vector_scores) if mode == "hybrid" else [0.0] * len(chunks)

    scored: list[RetrievedChunk] = []
    for c, lex_raw, vec_raw, lex_n, vec_n in zip(
        chunks, lexical_scores, vector_scores, lex_norm, vec_norm
    ):
        if lex_raw <= 0 and vec_raw <= 0:
            continue
        s = (
            _W_LEXICAL * lex_n
            + (_W_VECTOR * vec_n if mode == "hybrid" else 0.0)
            + _W_FRESHNESS * _freshness_boost(c.source.last_changed or c.source.last_checked)
        )
        scored.append(
            RetrievedChunk(
                chunk=c,
                source=c.source,
                score=round(s, 6),
                lexical_score=round(lex_raw, 6),
                vector_score=round(vec_raw, 6),
            )
        )

    scored.sort(key=lambda x: x.score, reverse=True)
    return scored[:top_k]
