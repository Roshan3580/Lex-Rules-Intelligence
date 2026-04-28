"""Bulk-ingest the curated source list in app/data/sources.yaml.

Each entry is fetched, cleaned, chunked, and run through rule extraction.
Sources whose checksum already exists are skipped (the existing row's
last_checked is bumped). Network failures are isolated per-source so one
bad URL doesn't kill the whole run.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml
from sqlalchemy.orm import Session

from . import ingestion_service

logger = logging.getLogger(__name__)

SOURCES_YAML = Path(__file__).resolve().parent.parent / "data" / "sources.yaml"


@dataclass
class SourceRunResult:
    name: str
    url: Optional[str]
    state: Optional[str]
    tax_type: Optional[str]
    status: str  # ingested | duplicate | error
    chunks_created: int = 0
    rules_created: int = 0
    extraction_method: Optional[str] = None
    error: Optional[str] = None


def load_seed_specs() -> list[dict[str, Any]]:
    if not SOURCES_YAML.exists():
        return []
    with SOURCES_YAML.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    raw = data.get("sources") or []
    return [s for s in raw if isinstance(s, dict)]


def run_seed_ingestion(
    db: Session,
    *,
    only_state: Optional[str] = None,
    only_tax_type: Optional[str] = None,
    auto_extract: bool = True,
) -> list[SourceRunResult]:
    """Iterate the seed list and ingest each entry. Returns per-source results."""
    specs = load_seed_specs()
    results: list[SourceRunResult] = []

    for spec in specs:
        url = spec.get("url")
        name = spec.get("name") or url or "(unnamed)"
        state = spec.get("state")
        tax_type = spec.get("tax_type") or spec.get("tax_category")

        if only_state and state != only_state:
            continue
        if only_tax_type and tax_type != only_tax_type:
            continue
        if not url:
            results.append(
                SourceRunResult(
                    name=name,
                    url=None,
                    state=state,
                    tax_type=tax_type,
                    status="error",
                    error="missing url",
                )
            )
            continue

        try:
            source, chunks, rules, method = ingestion_service.ingest_url(
                db,
                url=url,
                state=state,
                tax_category=tax_type,
                name=name,
                auto_extract=auto_extract,
                skip_if_duplicate=True,
            )
            results.append(
                SourceRunResult(
                    name=source.name,
                    url=source.url,
                    state=source.state,
                    tax_type=source.tax_category,
                    status="duplicate" if method == "duplicate" else "ingested",
                    chunks_created=chunks,
                    rules_created=rules,
                    extraction_method=method,
                )
            )
        except Exception as exc:  # pragma: no cover (network)
            logger.warning("Seed ingest failed for %s: %s", url, exc)
            results.append(
                SourceRunResult(
                    name=name,
                    url=url,
                    state=state,
                    tax_type=tax_type,
                    status="error",
                    error=str(exc)[:300],
                )
            )

    return results
