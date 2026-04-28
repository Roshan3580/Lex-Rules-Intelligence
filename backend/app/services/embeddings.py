"""Embedding provider abstraction.

Phase 5 of the upgrade plan. Three providers, all returning numpy float32
vectors with L2 normalisation so cosine similarity reduces to a dot product:

- `openai` — calls an OpenAI-compatible /embeddings endpoint. Works with
  OpenAI, OpenRouter, Together, Perplexity, etc. Groq does **not** currently
  expose embeddings, so users on Groq for chat may want to keep this as
  `hash` or set a separate OpenAI key just for embeddings.
- `hash`   — deterministic feature-hashing fallback. Doesn't require
  network. Quality is mediocre on cross-domain queries but useful enough
  to demonstrate hybrid retrieval offline (and matches deterministically,
  which is handy for tests).
- `none`   — disables embeddings; vector store and hybrid retrieval are
  no-ops.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Optional

import requests

try:  # numpy is required for the vector store + hash fallback.
    import numpy as np
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]

from ..config import settings

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]+")


class EmbeddingProvider:
    """Base class. Subclasses override `embed_one` and report `dim`."""

    name: str = "base"
    dim: int = 0

    @property
    def enabled(self) -> bool:
        return False

    def embed(self, texts: list[str]) -> "np.ndarray":  # type: ignore[name-defined]
        raise NotImplementedError

    def embed_one(self, text: str) -> "np.ndarray":  # type: ignore[name-defined]
        return self.embed([text])[0]


# ---------------------------------------------------------------------------
# Hash fallback
# ---------------------------------------------------------------------------


class HashEmbeddings(EmbeddingProvider):
    """Deterministic hashed-token embedding (no network).

    Buckets each token into a fixed-dim feature space using SHA-256 of
    `(token, slot)` pairs to fan-out per token. The result is L2-normalised
    so it sits on the unit sphere alongside real embeddings. The signal is
    weaker than a real model but strong enough that it consistently ranks
    documents containing the same vocabulary higher than unrelated ones.
    """

    name = "hash"

    def __init__(self, dim: int = 384) -> None:
        if np is None:
            raise RuntimeError("numpy is required for HashEmbeddings")
        self.dim = int(dim)

    @property
    def enabled(self) -> bool:
        return True

    def _vector_for(self, text: str) -> "np.ndarray":  # type: ignore[name-defined]
        vec = np.zeros(self.dim, dtype=np.float32)
        tokens = [t.lower() for t in _TOKEN_RE.findall(text or "")]
        if not tokens:
            return vec
        # Each token contributes to a small handful of slots so similar
        # vocabularies overlap meaningfully.
        for tok in tokens:
            for slot in range(3):
                h = hashlib.sha256(f"{tok}|{slot}".encode("utf-8")).digest()
                idx = int.from_bytes(h[:4], "big") % self.dim
                sign = 1.0 if (h[4] & 1) == 0 else -1.0
                vec[idx] += sign
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def embed(self, texts: list[str]) -> "np.ndarray":  # type: ignore[name-defined]
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        return np.stack([self._vector_for(t) for t in texts])


# ---------------------------------------------------------------------------
# OpenAI-compatible
# ---------------------------------------------------------------------------


class OpenAIEmbeddings(EmbeddingProvider):
    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        dim_hint: int = 1536,
        timeout: float = 30.0,
    ) -> None:
        if np is None:
            raise RuntimeError("numpy is required for OpenAIEmbeddings")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.dim = int(dim_hint)

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def embed(self, texts: list[str]) -> "np.ndarray":  # type: ignore[name-defined]
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        # Truncate per-input to avoid hitting model context limits. 8K chars
        # ~ 2K tokens, comfortable for text-embedding-3-* and most OSS models.
        cleaned = [(t or "")[:8000] for t in texts]
        r = requests.post(
            f"{self.base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={"model": self.model, "input": cleaned},
            timeout=self.timeout,
        )
        r.raise_for_status()
        data = r.json().get("data") or []
        vecs = np.array(
            [d.get("embedding") or [] for d in data], dtype=np.float32
        )
        if vecs.size == 0:
            return np.zeros((len(texts), self.dim), dtype=np.float32)
        # Normalise (OpenAI vectors are already ~unit-norm but third-party
        # OAI-compatible servers aren't always).
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        vecs = vecs / norms
        if vecs.shape[1] != self.dim:
            self.dim = int(vecs.shape[1])
        return vecs


# ---------------------------------------------------------------------------
# No-op
# ---------------------------------------------------------------------------


class NoOpEmbeddings(EmbeddingProvider):
    name = "none"
    dim = 0

    @property
    def enabled(self) -> bool:
        return False

    def embed(self, texts: list[str]):  # type: ignore[no-untyped-def]
        if np is None:
            return [[] for _ in texts]
        return np.zeros((len(texts), 0), dtype=np.float32)


# ---------------------------------------------------------------------------
# Factory + module-level singleton
# ---------------------------------------------------------------------------


def _build_provider() -> EmbeddingProvider:
    if np is None:
        logger.warning("numpy not installed — embeddings disabled")
        return NoOpEmbeddings()
    provider = (settings.embedding_provider or "").strip().lower()
    if provider == "openai":
        if not settings.embedding_api_key.strip():
            logger.warning(
                "EMBEDDING_PROVIDER=openai but EMBEDDING_API_KEY missing — "
                "falling back to hash provider"
            )
            return HashEmbeddings(dim=settings.embedding_dim)
        return OpenAIEmbeddings(
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_base_url,
            model=settings.embedding_model,
        )
    if provider == "hash":
        return HashEmbeddings(dim=settings.embedding_dim)
    return NoOpEmbeddings()


embedder: EmbeddingProvider = _build_provider()


def reload_provider() -> EmbeddingProvider:
    """Rebuild the singleton (used in tests when env vars change)."""
    global embedder
    embedder = _build_provider()
    return embedder
