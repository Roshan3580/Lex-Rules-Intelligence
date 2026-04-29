"""Application configuration.

Centralized settings loaded from environment variables / `.env`. The settings
object is intentionally simple: this is a modular monolith prototype and we
prefer one place to read config rather than scattering os.getenv calls.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./rules.db"

    # LLM provider (OpenAI-compatible). Empty key triggers deterministic
    # fallback so the app remains demoable without internet/keys.
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    frontend_origin: str = "http://localhost:5173"
    upload_dir: str = "./uploads"

    # When DEMO_MODE=true the backend will insert the illustrative
    # CA/TX/NY seed rules in app/seed.py so the app is demoable from
    # an empty DB. Default is False — production starts empty.
    demo_mode: bool = False

    # Governance: enforce extra publish fields (effective_date, etc.).
    strict_publish_checks: bool = False

    # ------------------------------------------------------------------
    # Embeddings / hybrid retrieval (Phase 5)
    # ------------------------------------------------------------------
    # `none`   — disable vectors, retrieval stays purely lexical.
    # `openai` — call an OpenAI-compatible embeddings endpoint.
    # `hash`   — deterministic hash-based embedding fallback (offline).
    embedding_provider: str = "hash"
    embedding_api_key: str = ""
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 384  # used by hash fallback

    # Vector store backend. Today only `numpy` is implemented (in-process
    # numpy matrix persisted to disk). pgvector / chroma slots are reserved
    # for later phases.
    vector_backend: str = "numpy"
    vector_index_dir: str = "./.vector_index"

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def vector_index_path(self) -> Path:
        p = Path(self.vector_index_dir).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key.strip())

    @property
    def embeddings_enabled(self) -> bool:
        provider = (self.embedding_provider or "").strip().lower()
        if provider == "none":
            return False
        if provider == "openai":
            return bool(self.embedding_api_key.strip())
        if provider == "hash":
            return True
        return False

    @property
    def vector_enabled(self) -> bool:
        return self.embeddings_enabled and (self.vector_backend or "").lower() == "numpy"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# Convenience handle for modules that need it at import time.
settings = get_settings()
os.makedirs(settings.upload_dir, exist_ok=True)
