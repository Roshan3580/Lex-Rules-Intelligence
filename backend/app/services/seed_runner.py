"""Bulk-ingest the curated source list in app/data/sources.yaml.

Each entry is fetched, cleaned, chunked, and run through rule extraction.
Sources whose checksum already exists are skipped (the existing row's
last_checked is bumped). Network failures are isolated per-source so one
bad URL doesn't kill the whole run.

Every batch run records an `IngestionRun` row with one `IngestionRunItem`
per source attempted, so `GET /api/ingest/runs` can replay history.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml
from sqlalchemy.orm import Session

from .. import models
from . import ingestion_runs, ingestion_service

logger = logging.getLogger(__name__)

SOURCES_YAML = Path(__file__).resolve().parent.parent / "data" / "sources.yaml"


@dataclass
class SourceRunResult:
    name: str
    url: Optional[str]
    state: Optional[str]
    tax_type: Optional[str]
    status: str  # ingested | duplicate | error | updated
    chunks_created: int = 0
    rules_created: int = 0
    extraction_method: Optional[str] = None
    error: Optional[str] = None
    source_id: Optional[str] = None


def load_seed_specs() -> list[dict[str, Any]]:
    if not SOURCES_YAML.exists():
        return []
    with SOURCES_YAML.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    raw = data.get("sources") or []
    return [s for s in raw if isinstance(s, dict)]


def _expand_with_crawl(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """If a spec sets crawl_depth>0, expand into a list of (start_url, …)
    plus discovered links. The expanded specs reuse the parent's state /
    tax_type so the children inherit the right metadata.
    """
    depth = int(spec.get("crawl_depth") or 0)
    if depth <= 0 or not spec.get("url"):
        return [spec]
    max_pages = int(spec.get("crawl_max_pages") or 5)
    try:
        urls = ingestion_service.crawl_links(
            spec["url"], depth=depth, max_pages=max_pages
        )
    except Exception as exc:  # pragma: no cover (network)
        logger.warning("Crawl failed for %s: %s", spec.get("url"), exc)
        urls = [spec["url"]]
    expanded: list[dict[str, Any]] = []
    for i, url in enumerate(urls):
        item = dict(spec)
        item["url"] = url
        item.pop("crawl_depth", None)
        item.pop("crawl_max_pages", None)
        if i > 0 and item.get("name"):
            item["name"] = f"{spec['name']} — {url}"
        expanded.append(item)
    return expanded


def run_seed_ingestion(
    db: Session,
    *,
    only_state: Optional[str] = None,
    only_tax_type: Optional[str] = None,
    auto_extract: bool = True,
    triggered_by: Optional[str] = "yaml",
) -> tuple[models.IngestionRun, list[SourceRunResult]]:
    """Iterate the seed list and ingest each entry. Returns (run, per-source results)."""
    specs = load_seed_specs()
    run = ingestion_runs.start_run(
        db,
        kind="yaml",
        only_state=only_state,
        only_tax_type=only_tax_type,
        triggered_by=triggered_by,
        notes=f"{len(specs)} specs in sources.yaml",
    )

    results: list[SourceRunResult] = []
    expanded_specs: list[dict[str, Any]] = []
    for spec in specs:
        expanded_specs.extend(_expand_with_crawl(spec))

    for spec in expanded_specs:
        url = spec.get("url")
        name = spec.get("name") or url or "(unnamed)"
        state = spec.get("state")
        tax_type = spec.get("tax_type") or spec.get("tax_category")

        if only_state and state != only_state:
            continue
        if only_tax_type and tax_type != only_tax_type:
            continue
        if not url:
            ingestion_runs.record_item(
                db,
                run,
                name=name,
                url=None,
                state=state,
                tax_category=tax_type,
                status="failed",
                error_message="missing url",
            )
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
            status = (
                "duplicate"
                if method == "duplicate"
                else "updated"
                if method == "updated"
                else "ingested"
            )
            ingestion_runs.record_item(
                db,
                run,
                source=source,
                status=status,
                chunks_created=chunks,
                rules_created=rules,
                extraction_method=method,
            )
            results.append(
                SourceRunResult(
                    name=source.name,
                    url=source.url,
                    state=source.state,
                    tax_type=source.tax_category,
                    status=status,
                    chunks_created=chunks,
                    rules_created=rules,
                    extraction_method=method,
                    source_id=source.id,
                )
            )
        except Exception as exc:  # pragma: no cover (network)
            logger.warning("Seed ingest failed for %s: %s", url, exc)
            ingestion_runs.record_item(
                db,
                run,
                name=name,
                url=url,
                state=state,
                tax_category=tax_type,
                status="failed",
                error_message=str(exc),
            )
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

    ingestion_runs.finish_run(db, run)
    return run, results
