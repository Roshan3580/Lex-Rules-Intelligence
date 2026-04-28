"""Thin LLM abstraction.

We talk to any OpenAI-compatible chat-completions endpoint. Configuring
LLM_BASE_URL/LLM_API_KEY/LLM_MODEL is all that's required to swap providers
(OpenAI, Azure OpenAI proxy, OpenRouter, local vLLM, etc.). When no API key
is configured the client reports llm_enabled=False and callers fall back to
deterministic logic — no network calls happen.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self) -> None:
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_base_url.rstrip("/")
        self.model = settings.llm_model

    @property
    def enabled(self) -> bool:
        return bool(self.api_key.strip())

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 1200,
        response_format: Optional[dict[str, Any]] = None,
        timeout: float = 60.0,
    ) -> str:
        """Call chat completions and return the assistant text content.

        Raises an exception on transport failure so callers can decide
        whether to surface the error or fall back.
        """
        if not self.enabled:
            raise RuntimeError("LLM is not configured (LLM_API_KEY is empty).")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            payload["response_format"] = response_format

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=timeout) as client:
            r = client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()

        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError) as exc:
            raise RuntimeError(f"Unexpected LLM response shape: {data}") from exc

    def chat_json(self, messages: list[dict[str, str]], **kwargs: Any) -> Any:
        """Call chat() and parse the response as JSON, lenient about fences."""
        text = self.chat(
            messages,
            response_format={"type": "json_object"},
            **kwargs,
        )
        return _parse_json_lenient(text)


def _parse_json_lenient(text: str) -> Any:
    """Best-effort JSON parse: strips ``` fences and isolates the first object."""
    text = (text or "").strip()
    if text.startswith("```"):
        # Strip ```json fences
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Find the outermost JSON object/array.
        start = min((i for i in (text.find("{"), text.find("[")) if i != -1), default=-1)
        end = max(text.rfind("}"), text.rfind("]"))
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        logger.warning("LLM returned non-JSON content: %s", text[:200])
        return None


llm_client = LLMClient()
