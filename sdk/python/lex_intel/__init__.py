"""Lex Intelligence API — minimal Python client stub."""

from __future__ import annotations

from typing import Any, Optional

import httpx


class LexIntelClient:
    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def validate_submission(self, body: dict[str, Any]) -> dict[str, Any]:
        r = self._client.post("/api/validate-submission", json=body)
        r.raise_for_status()
        return r.json()

    def submission_path(
        self,
        *,
        state: str,
        tax_category: str,
        workflow_stage: Optional[str] = None,
        transaction_type: Optional[str] = None,
    ) -> dict[str, Any]:
        params: dict[str, str] = {"state": state, "tax_category": tax_category}
        if workflow_stage:
            params["workflow_stage"] = workflow_stage
        if transaction_type:
            params["transaction_type"] = transaction_type
        r = self._client.get("/api/submission-path", params=params)
        r.raise_for_status()
        return r.json()

    def close(self) -> None:
        self._client.close()
