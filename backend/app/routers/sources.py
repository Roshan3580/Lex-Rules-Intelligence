"""Source ingestion + listing endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..services import ingestion_service

router = APIRouter(prefix="/api/sources", tags=["sources"])


def _to_out(source: models.Source, db: Session) -> schemas.SourceOut:
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
        file_path=source.file_path,
        state=source.state,
        tax_category=source.tax_category,
        status=source.status,
        created_at=source.created_at,
        updated_at=source.updated_at,
        chunk_count=chunk_count,
        rule_count=rule_count,
    )


@router.get("", response_model=list[schemas.SourceOut])
def list_sources(
    state: Optional[str] = None,
    tax_category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.Source)
    if state:
        q = q.filter(models.Source.state == state)
    if tax_category:
        q = q.filter(models.Source.tax_category == tax_category)
    sources = q.order_by(models.Source.created_at.desc()).all()
    return [_to_out(s, db) for s in sources]


@router.get("/{source_id}", response_model=schemas.SourceDetail)
def get_source(source_id: str, db: Session = Depends(get_db)):
    src = db.query(models.Source).filter(models.Source.id == source_id).first()
    if src is None:
        raise HTTPException(status_code=404, detail="Source not found")
    base = _to_out(src, db).model_dump()
    return schemas.SourceDetail(
        **base,
        raw_text_preview=(src.raw_text or "")[:4000],
        meta=src.meta,
    )


@router.post("/upload", response_model=schemas.IngestResult)
async def upload_source(
    file: UploadFile = File(...),
    state: Optional[str] = Form(default=None),
    tax_category: Optional[str] = Form(default=None),
    auto_extract: bool = Form(default=True),
    db: Session = Depends(get_db),
):
    try:
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="Empty upload")
        source, chunks, rules, method = ingestion_service.ingest_upload(
            db,
            filename=file.filename or "upload",
            data=data,
            state=state,
            tax_category=tax_category,
            auto_extract=auto_extract,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")
    return schemas.IngestResult(
        source=_to_out(source, db),
        chunks_created=chunks,
        rules_created=rules,
        extraction_method=method,
    )


@router.post("/url", response_model=schemas.IngestResult)
def ingest_url_endpoint(
    payload: schemas.IngestUrlRequest,
    db: Session = Depends(get_db),
):
    try:
        source, chunks, rules, method = ingestion_service.ingest_url(
            db,
            url=payload.url,
            state=payload.state,
            tax_category=payload.tax_category,
            name=payload.name,
            auto_extract=payload.auto_extract,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"URL ingestion failed: {exc}")
    return schemas.IngestResult(
        source=_to_out(source, db),
        chunks_created=chunks,
        rules_created=rules,
        extraction_method=method,
    )


@router.post("/text", response_model=schemas.IngestResult)
def ingest_text_endpoint(
    payload: schemas.IngestTextRequest,
    db: Session = Depends(get_db),
):
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Empty text")
    source, chunks, rules, method = ingestion_service.ingest_text(
        db,
        name=payload.name,
        text=payload.text,
        state=payload.state,
        tax_category=payload.tax_category,
        auto_extract=payload.auto_extract,
    )
    return schemas.IngestResult(
        source=_to_out(source, db),
        chunks_created=chunks,
        rules_created=rules,
        extraction_method=method,
    )


@router.delete("/{source_id}")
def delete_source(source_id: str, db: Session = Depends(get_db)):
    src = db.query(models.Source).filter(models.Source.id == source_id).first()
    if src is None:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(src)
    db.commit()
    return {"deleted": source_id}
