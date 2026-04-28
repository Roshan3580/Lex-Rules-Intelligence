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

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# Convenience handle for modules that need it at import time.
settings = get_settings()
os.makedirs(settings.upload_dir, exist_ok=True)
