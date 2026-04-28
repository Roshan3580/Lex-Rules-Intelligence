"""Spec-shaped ingestion endpoints: /api/ingest/source, /api/ingest/run.

These wrap the underlying ingestion_service in the way the engineering
brief / frontend expects (a single source-add endpoint that accepts URL
or pasted text, plus a batch runner that loads the curated YAML).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..services import ingestion_service, seed_runner

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


@router.post("/source", response_model=schemas.IngestResult)
def ingest_source(
    payload: schemas.IngestSourceRequest,
    db: Session = Depends(get_db),
):
    """Add a single source (URL, manual text, or PDF URL) to the index."""
    st = (payload.source_type or "").lower()

    try:
        if st in ("url", "webpage", "pdf", "html") or (payload.url and not payload.text):
            if not payload.url:
                raise HTTPException(
                    status_code=400,
                    detail="url is required for source_type=" + (st or "url"),
                )
            source, chunks, rules, method = ingestion_service.ingest_url(
                db,
                url=payload.url,
                state=payload.state,
                tax_category=payload.tax_type,
                name=payload.title,
                auto_extract=payload.auto_extract,
                skip_if_duplicate=True,
            )
        elif st in ("text", "manual"):
            if not payload.text:
                raise HTTPException(
                    status_code=400,
                    detail="text is required for source_type=manual/text",
                )
            source, chunks, rules, method = ingestion_service.ingest_text(
                db,
                name=payload.title or "Manual entry",
                text=payload.text,
                state=payload.state,
                tax_category=payload.tax_type,
                auto_extract=payload.auto_extract,
                source_type="manual",
                url=payload.url,
                skip_if_duplicate=False,
            )
        else:
            raise HTTPException(
                status_code=400, detail=f"Unknown source_type: {payload.source_type}"
            )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")

    chunk_count = (
        db.query(ingestion_service.models.SourceChunk)
        .filter(ingestion_service.models.SourceChunk.source_id == source.id)
        .count()
    )
    rule_count = (
        db.query(ingestion_service.models.Rule)
        .filter(ingestion_service.models.Rule.source_id == source.id)
        .count()
    )

    return schemas.IngestResult(
        source=schemas.SourceOut(
            id=source.id,
            source_type=source.source_type,
            name=source.name,
            url=source.url,
            file_path=source.file_path,
            state=source.state,
            tax_category=source.tax_category,
            status=source.status,
            created_at=source.created_at,
            updated_at=source.updated_at,
            chunk_count=chunk_count,
            rule_count=rule_count,
        ),
        chunks_created=chunks,
        rules_created=rules,
        extraction_method=method,
    )


@router.post("/run", response_model=schemas.IngestRunResult)
def ingest_run(
    payload: schemas.IngestRunRequest | None = None,
    db: Session = Depends(get_db),
):
    """Run ingestion for the curated source list in app/data/sources.yaml."""
    payload = payload or schemas.IngestRunRequest()
    results = seed_runner.run_seed_ingestion(
        db,
        only_state=payload.only_state,
        only_tax_type=payload.only_tax_type,
        auto_extract=payload.auto_extract,
    )
    items = [schemas.IngestRunItem(**r.__dict__) for r in results]
    ingested = sum(1 for r in results if r.status == "ingested")
    duplicates = sum(1 for r in results if r.status == "duplicate")
    errors = sum(1 for r in results if r.status == "error")
    return schemas.IngestRunResult(
        total=len(results),
        ingested=ingested,
        duplicates=duplicates,
        errors=errors,
        items=items,
    )
