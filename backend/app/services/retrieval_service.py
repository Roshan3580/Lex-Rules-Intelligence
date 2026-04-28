"""Retrieval service.

Lexical retrieval over rules and source chunks. We deliberately avoid an
external vector store in v1 — for hundreds to low-thousands of rules a
TF-style scoring function with state/category prefilters returns excellent
results and is dependency-free. The interface is structured so a future
pgvector / Qdrant backend can drop in without changing callers.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from .. import models

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


@dataclass
class RetrievedChunk:
    chunk: models.SourceChunk
    source: models.Source
    score: float


def retrieve_rules(
    db: Session,
    query: str,
    *,
    state: Optional[str] = None,
    tax_category: Optional[str] = None,
    top_k: int = 6,
    statuses: Optional[list[str]] = None,
) -> list[RetrievedRule]:
    """Return the top-k rules for a query, filtered by state/category."""
    q = db.query(models.Rule)
    if state:
        q = q.filter(models.Rule.state == state)
    if tax_category:
        q = q.filter(models.Rule.tax_category == tax_category)
    if statuses:
        q = q.filter(models.Rule.review_status.in_(statuses))
    rules = q.all()
    if not rules:
        return []

    tokens = _tokenize(query)
    scored: list[RetrievedRule] = []
    for r in rules:
        haystack = " ".join(
            filter(
                None,
                [
                    r.rule_title,
                    r.rule_summary,
                    r.detailed_rule or "",
                    " ".join(r.required_actions or []),
                    " ".join(r.required_forms or []),
                    " ".join(r.deadlines or []),
                    " ".join(r.conditions or []),
                    " ".join(r.exceptions or []),
                    r.source_snippet or "",
                ],
            )
        )
        score = _score(tokens, haystack)
        # Boost rules whose published/approved status indicates trust.
        if r.review_status in ("published", "approved"):
            score *= 1.2
        if score > 0:
            scored.append(RetrievedRule(rule=r, score=score))

    scored.sort(key=lambda x: x.score, reverse=True)
    return scored[:top_k]


def retrieve_chunks(
    db: Session,
    query: str,
    *,
    state: Optional[str] = None,
    tax_category: Optional[str] = None,
    top_k: int = 6,
) -> list[RetrievedChunk]:
    """Return the top-k source chunks for a query."""
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
    scored: list[RetrievedChunk] = []
    for c in chunks:
        score = _score(tokens, c.text)
        if score > 0:
            scored.append(RetrievedChunk(chunk=c, source=c.source, score=score))

    scored.sort(key=lambda x: x.score, reverse=True)
    return scored[:top_k]
