"""In-process numpy vector store for source chunks.

Persisted to a single pickle file under `settings.vector_index_path`. We're
intentionally not using ChromaDB / FAISS / pgvector for the prototype —
hundreds to low-thousands of chunks fit comfortably in memory, and a numpy
matrix + a tiny metadata dict gives us a transparent, debuggable index
that ships without extra system dependencies.

The interface is structured so a future backend swap (pgvector when running
on Postgres, Chroma when going to production) can land without touching
callers.
"""

from __future__ import annotations

import logging
import pickle
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]

from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from .embeddings import embedder

logger = logging.getLogger(__name__)


@dataclass
class _IndexEntry:
    chunk_id: str
    source_id: str
    state: Optional[str] = None
    tax_category: Optional[str] = None
    text: str = ""
    chunk_index: int = 0


@dataclass
class VectorMatch:
    chunk_id: str
    source_id: str
    state: Optional[str]
    tax_category: Optional[str]
    score: float
    chunk_index: int = 0


@dataclass
class _IndexState:
    dim: int = 0
    matrix: object = None  # np.ndarray
    entries: list[_IndexEntry] = field(default_factory=list)


class NumpyVectorStore:
    """Thread-safe singleton index. Loads from disk lazily on first use."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._state = _IndexState()
        self._loaded = False

    # --- persistence --------------------------------------------------

    def _file(self) -> Path:
        return settings.vector_index_path / "index.pkl"

    def _load(self) -> None:
        if self._loaded or np is None:
            self._loaded = True
            return
        path = self._file()
        if path.exists():
            try:
                with path.open("rb") as f:
                    data = pickle.load(f)
                self._state = _IndexState(
                    dim=int(data.get("dim", 0)),
                    matrix=data.get("matrix"),
                    entries=list(data.get("entries", [])),
                )
                logger.info(
                    "Vector index loaded: %d entries, dim=%d",
                    len(self._state.entries),
                    self._state.dim,
                )
            except Exception as exc:  # pragma: no cover - corruption
                logger.warning("Vector index load failed (%s); starting fresh", exc)
                self._state = _IndexState()
        self._loaded = True

    def _save(self) -> None:
        if np is None:
            return
        path = self._file()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".pkl.tmp")
        with tmp.open("wb") as f:
            pickle.dump(
                {
                    "dim": self._state.dim,
                    "matrix": self._state.matrix,
                    "entries": self._state.entries,
                },
                f,
                protocol=pickle.HIGHEST_PROTOCOL,
            )
        tmp.replace(path)

    # --- public API ---------------------------------------------------

    def stats(self) -> dict:
        with self._lock:
            self._load()
            return {
                "size": len(self._state.entries),
                "dim": self._state.dim,
                "backend": settings.vector_backend,
                "embedder": embedder.name,
                "enabled": settings.vector_enabled and embedder.enabled,
            }

    def clear(self) -> None:
        with self._lock:
            self._state = _IndexState()
            self._loaded = True
            self._save()

    def remove_source(self, source_id: str) -> int:
        with self._lock:
            self._load()
            if not self._state.entries:
                return 0
            keep_idx = [
                i
                for i, e in enumerate(self._state.entries)
                if e.source_id != source_id
            ]
            removed = len(self._state.entries) - len(keep_idx)
            if removed == 0:
                return 0
            self._state.entries = [self._state.entries[i] for i in keep_idx]
            if np is not None and self._state.matrix is not None and keep_idx:
                self._state.matrix = self._state.matrix[keep_idx]  # type: ignore[index]
            elif not keep_idx:
                self._state.matrix = None
            self._save()
            return removed

    def index_chunks(
        self,
        db: Session,
        source: models.Source,
        *,
        replace: bool = True,
    ) -> int:
        """Embed and index all chunks for a source. Returns count added."""
        if not (settings.vector_enabled and embedder.enabled):
            return 0
        if np is None:
            return 0
        chunks = (
            db.query(models.SourceChunk)
            .filter(models.SourceChunk.source_id == source.id)
            .order_by(models.SourceChunk.chunk_index.asc())
            .all()
        )
        if not chunks:
            return 0
        with self._lock:
            self._load()
            if replace:
                self.remove_source(source.id)
                self._load()

            try:
                vecs = embedder.embed([c.text or "" for c in chunks])
            except Exception as exc:
                logger.warning(
                    "Embedding failed for source %s: %s", source.id, exc
                )
                return 0
            if vecs is None or vecs.shape[0] == 0:
                return 0

            entries = [
                _IndexEntry(
                    chunk_id=c.id,
                    source_id=c.source_id,
                    state=c.state or source.state,
                    tax_category=c.tax_category or source.tax_category,
                    text=(c.text or "")[:1500],
                    chunk_index=c.chunk_index,
                )
                for c in chunks
            ]

            if self._state.matrix is None or self._state.matrix.shape[0] == 0:  # type: ignore[union-attr]
                self._state.matrix = vecs.astype(np.float32)
                self._state.dim = int(vecs.shape[1])
                self._state.entries = list(entries)
            else:
                if vecs.shape[1] != self._state.matrix.shape[1]:  # type: ignore[union-attr]
                    logger.warning(
                        "Embedding dim changed (%d -> %d); rebuilding index",
                        self._state.matrix.shape[1],  # type: ignore[union-attr]
                        vecs.shape[1],
                    )
                    self._state = _IndexState(
                        dim=int(vecs.shape[1]),
                        matrix=vecs.astype(np.float32),
                        entries=list(entries),
                    )
                else:
                    self._state.matrix = np.vstack(
                        [self._state.matrix, vecs.astype(np.float32)]
                    )
                    self._state.entries.extend(entries)
            self._save()
            return len(entries)

    def query(
        self,
        text: str,
        *,
        state: Optional[str] = None,
        tax_category: Optional[str] = None,
        top_k: int = 12,
        min_score: float = 0.0,
    ) -> list[VectorMatch]:
        if not (settings.vector_enabled and embedder.enabled):
            return []
        if np is None:
            return []
        with self._lock:
            self._load()
            if self._state.matrix is None or not self._state.entries:
                return []
            try:
                qvec = embedder.embed_one(text or "")
            except Exception as exc:
                logger.warning("Query embedding failed: %s", exc)
                return []
            if qvec is None or qvec.size == 0:
                return []
            if qvec.shape[0] != self._state.matrix.shape[1]:  # type: ignore[union-attr]
                logger.warning(
                    "Query dim %d != index dim %d", qvec.shape[0], self._state.matrix.shape[1]  # type: ignore[union-attr]
                )
                return []
            sims = (self._state.matrix @ qvec).astype(float)  # type: ignore[union-attr]

            order = np.argsort(-sims)
            out: list[VectorMatch] = []
            for i in order:
                if len(out) >= top_k:
                    break
                e = self._state.entries[int(i)]
                if state and (e.state or "") != state:
                    continue
                if tax_category and (e.tax_category or "") != tax_category:
                    continue
                score = float(sims[int(i)])
                if score < min_score:
                    break
                out.append(
                    VectorMatch(
                        chunk_id=e.chunk_id,
                        source_id=e.source_id,
                        state=e.state,
                        tax_category=e.tax_category,
                        score=score,
                        chunk_index=e.chunk_index,
                    )
                )
            return out

    def rebuild_from_db(self, db: Session) -> int:
        """Drop the index and re-embed every chunk in the DB. Used by the
        admin "rebuild index" action."""
        with self._lock:
            self.clear()
            sources = db.query(models.Source).all()
            total = 0
            for s in sources:
                total += self.index_chunks(db, s, replace=False)
            return total


vector_store = NumpyVectorStore()
