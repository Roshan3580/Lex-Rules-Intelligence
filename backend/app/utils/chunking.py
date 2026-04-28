"""Text chunking utilities.

The retrieval layer needs reasonably sized chunks with sentence-aware
boundaries. For a v1 prototype we use a simple paragraph-then-sentence
splitter with a soft target chunk size and a small overlap. This avoids the
heavyweight tokenizer dependency while still yielding chunks that retrieve
well.
"""

from __future__ import annotations

import re

DEFAULT_CHUNK_SIZE = 900  # characters (rough proxy for ~200 tokens)
DEFAULT_OVERLAP = 120


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")


def _split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    return [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[str]:
    """Chunk arbitrary text into roughly chunk_size-character segments.

    We greedily pack sentences into chunks. When a single sentence is longer
    than chunk_size we hard-split it. Overlap is implemented by carrying the
    tail of the previous chunk forward as a prefix.
    """
    text = (text or "").strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    sentences: list[str] = []
    for p in paragraphs:
        sentences.extend(_split_sentences(p))

    chunks: list[str] = []
    current = ""
    for sent in sentences:
        if len(sent) > chunk_size:
            # Flush current and hard-split the long sentence.
            if current:
                chunks.append(current.strip())
                current = ""
            for i in range(0, len(sent), chunk_size):
                chunks.append(sent[i : i + chunk_size].strip())
            continue

        if len(current) + len(sent) + 1 <= chunk_size:
            current = (current + " " + sent).strip()
        else:
            if current:
                chunks.append(current.strip())
            tail = current[-overlap:] if overlap and current else ""
            current = (tail + " " + sent).strip()

    if current.strip():
        chunks.append(current.strip())

    return [c for c in chunks if c]
