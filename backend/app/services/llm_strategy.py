"""Routing between cheap / premium LLM callers — extraction only; never enforcement."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

from ..config import settings


def cache_key(*, source_checksum: str, prompt_version: str, model: str) -> str:
    raw = f"{source_checksum}|{prompt_version}|{model}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def select_model(*, task: str, prefer_quality: bool = False) -> str:
    """Cheap default; expensive when ``prefer_quality`` or task == deep_extract."""
    base = (settings.llm_model or "gpt-4o-mini").strip()
    if prefer_quality or task in ("deep_extract", "conflict_resolution"):
        return "gpt-4o" if "mini" in base else base
    return base


def should_use_llm_for_enforcement() -> bool:
    return False
