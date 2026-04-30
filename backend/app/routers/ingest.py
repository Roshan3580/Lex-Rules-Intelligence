"""Spec-shaped ingestion endpoints.

- POST /api/ingest/source        Add a single source (URL/text/PDF), optionally
                                 with shallow crawl.
- POST /api/ingest/run           Run the curated YAML batch.
- GET  /api/ingest/runs          List ingestion run history.
- GET  /api/ingest/runs/{id}     Inspect one run with its per-source items.

Every code path here is wrapped in an `IngestionRun`/`IngestionRunItem` row
so we always have an audit trail of what was attempted and what happened.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..middleware.rbac import require_role, tenant_id_dep
from ..services import audit_service, ingestion_runs, ingestion_service, seed_runner
from ..services.cache_service import invalidate_enforcement_caches

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _source_to_out(source: models.Source, db: Session) -> schemas.SourceOut:
    chunk_count = (
        db.query(models.SourceChunk)
        .filter(models.SourceChunk.source_id == source.id)
        .count()
    )
    rule_count = (
        db.query(models.Rule).filter(models.Rule.source_id == source.id).count()
    )
    return schemas.SourceOut(
        id=source.id,
        source_type=source.source_type,
        name=source.name,
        url=source.url,
        canonical_url=source.canonical_url,
        file_path=source.file_path,
        state=source.state,
        tax_category=source.tax_category,
        status=source.status,
        error_message=source.error_message,
        checksum=source.checksum,
        last_checked=source.last_checked,
        last_changed=source.last_changed,
        current_version=source.current_version,
        created_at=source.created_at,
        updated_at=source.updated_at,
        chunk_count=chunk_count,
        rule_count=rule_count,
    )


def _item_from_db(it: models.IngestionRunItem) -> schemas.IngestRunItem:
    return schemas.IngestRunItem(
        name=it.name,
        url=it.url,
        state=it.state,
        tax_type=it.tax_category,
        source_id=it.source_id,
        source_type=it.source_type,
        status=it.status,
        chunks_created=it.chunks_created,
        rules_created=it.rules_created,
        extraction_method=it.extraction_method,
        error=it.error_message,
        error_message=it.error_message,
        created_at=it.created_at,
    )


def _ingest_one_url(
    db: Session,
    run: models.IngestionRun,
    *,
    tenant_id: str,
    url: str,
    state: Optional[str],
    tax_type: Optional[str],
    name: Optional[str],
    auto_extract: bool,
) -> tuple[Optional[models.Source], int, int, str]:
    try:
        source, chunks, rules, method = ingestion_service.ingest_url(
            db,
            tenant_id=tenant_id,
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
        return source, chunks, rules, method
    except Exception as exc:
        ingestion_runs.record_item(
            db,
            run,
            name=name or url,
            url=url,
            state=state,
            tax_category=tax_type,
            status="failed",
            error_message=f"{type(exc).__name__}: {exc}",
        )
        return None, 0, 0, "failed"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/source", response_model=schemas.IngestRunResult)
def ingest_source(
    payload: schemas.IngestSourceRequest,
    request: Request,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("admin")),
    tenant_id: str = Depends(tenant_id_dep),
):
    """Add a single source (URL, manual text, or PDF URL) to the index.

    If `crawl_depth > 0` and the source is a URL, we walk same-host links up
    to the requested depth/page cap and ingest each one. The whole call is
    wrapped in a single IngestionRun so its history is queryable.
    """
    st = (payload.source_type or "").lower()
    is_url_kind = st in ("url", "webpage", "pdf", "html") or (
        payload.url and not payload.text
    )
    is_text_kind = st in ("text", "manual")

    if not is_url_kind and not is_text_kind:
        raise HTTPException(
            status_code=400, detail=f"Unknown source_type: {payload.source_type}"
        )
    if is_url_kind and not payload.url:
        raise HTTPException(status_code=400, detail="url is required")
    if is_text_kind and not payload.text:
        raise HTTPException(status_code=400, detail="text is required")

    kind = "crawl" if (is_url_kind and payload.crawl_depth > 0) else (
        "single" if is_url_kind else "text"
    )
    run = ingestion_runs.start_run(
        db,
        kind=kind,
        triggered_by="api:/api/ingest/source",
        notes=f"source_type={payload.source_type}",
    )
    audit_service.log(
        db,
        action="ingestion_run_started",
        resource_type="ingestion_run",
        resource_id=run.id,
        actor=getattr(request.state, "user_id", None),
        detail={"trigger_api": "/api/ingest/source", "run_kind": kind},
    )

    try:
        if is_text_kind:
            try:
                source, chunks, rules, method = ingestion_service.ingest_text(
                    db,
                    tenant_id=tenant_id,
                    name=payload.title or "Manual entry",
                    text=payload.text or "",
                    state=payload.state,
                    tax_category=payload.tax_type,
                    auto_extract=payload.auto_extract,
                    source_type="manual",
                    url=payload.url,
                    skip_if_duplicate=False,
                )
                ingestion_runs.record_item(
                    db,
                    run,
                    source=source,
                    status="ingested",
                    chunks_created=chunks,
                    rules_created=rules,
                    extraction_method=method,
                )
            except Exception as exc:
                ingestion_runs.record_item(
                    db,
                    run,
                    name=payload.title or "Manual entry",
                    url=payload.url,
                    state=payload.state,
                    tax_category=payload.tax_type,
                    status="failed",
                    error_message=f"{type(exc).__name__}: {exc}",
                )
        else:
            urls = [payload.url]
            if payload.crawl_depth > 0:
                try:
                    urls = ingestion_service.crawl_links(
                        payload.url,
                        depth=payload.crawl_depth,
                        max_pages=max(1, min(payload.crawl_max_pages, 25)),
                    )
                except Exception as exc:
                    ingestion_runs.record_item(
                        db,
                        run,
                        name=payload.title or payload.url,
                        url=payload.url,
                        state=payload.state,
                        tax_category=payload.tax_type,
                        status="failed",
                        error_message=f"crawl failed: {exc}",
                    )
                    urls = []

            for i, u in enumerate(urls):
                _ingest_one_url(
                    db,
                    run,
                    tenant_id=tenant_id,
                    url=u,
                    state=payload.state,
                    tax_type=payload.tax_type,
                    name=payload.title if i == 0 else None,
                    auto_extract=payload.auto_extract,
                )
    finally:
        ingestion_runs.finish_run(db, run)

    invalidate_enforcement_caches()

    items_db = (
        db.query(models.IngestionRunItem)
        .filter(models.IngestionRunItem.run_id == run.id)
        .order_by(models.IngestionRunItem.created_at.asc())
        .all()
    )
    return schemas.IngestRunResult(
        total=run.total,
        ingested=run.ingested,
        duplicates=run.duplicates,
        errors=run.errors,
        items=[_item_from_db(it) for it in items_db],
        run_id=run.id,
    )


@router.post("/run", response_model=schemas.IngestRunResult)
def ingest_run(
    request: Request,
    payload: schemas.IngestRunRequest | None = None,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("admin")),
    tenant_id: str = Depends(tenant_id_dep),
):
    """Run ingestion for the curated source list in app/data/sources.yaml."""
    payload = payload or schemas.IngestRunRequest()
    run, results = seed_runner.run_seed_ingestion(
        db,
        tenant_id=tenant_id,
        only_state=payload.only_state,
        only_tax_type=payload.only_tax_type,
        auto_extract=payload.auto_extract,
    )
    audit_service.log(
        db,
        action="ingestion_run_started",
        resource_type="ingestion_run",
        resource_id=run.id,
        actor=getattr(request.state, "user_id", None),
        detail={"trigger_api": "/api/ingest/run", "run_kind": run.kind},
    )

    items = [
        schemas.IngestRunItem(
            name=r.name,
            url=r.url,
            state=r.state,
            tax_type=r.tax_type,
            source_id=r.source_id,
            status=(
                "failed"
                if r.status == "error"
                else r.status
            ),
            chunks_created=r.chunks_created,
            rules_created=r.rules_created,
            extraction_method=r.extraction_method,
            error=r.error,
            error_message=r.error,
        )
        for r in results
    ]
    invalidate_enforcement_caches()
    return schemas.IngestRunResult(
        total=run.total,
        ingested=run.ingested,
        duplicates=run.duplicates,
        errors=run.errors,
        items=items,
        run_id=run.id,
    )


@router.get("/runs", response_model=list[schemas.IngestionRunOut])
def list_runs(
    limit: int = 50,
    db: Session = Depends(get_db),
):
    rows = (
        db.query(models.IngestionRun)
        .order_by(models.IngestionRun.started_at.desc())
        .limit(max(1, min(limit, 200)))
        .all()
    )
    return [schemas.IngestionRunOut.model_validate(r) for r in rows]


@router.get("/runs/{run_id}", response_model=schemas.IngestionRunDetail)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = (
        db.query(models.IngestionRun).filter(models.IngestionRun.id == run_id).first()
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    items = (
        db.query(models.IngestionRunItem)
        .filter(models.IngestionRunItem.run_id == run.id)
        .order_by(models.IngestionRunItem.created_at.asc())
        .all()
    )
    base = schemas.IngestionRunOut.model_validate(run).model_dump()
    return schemas.IngestionRunDetail(
        **base,
        items=[_item_from_db(it) for it in items],
    )
