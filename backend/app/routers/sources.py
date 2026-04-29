"""Source ingestion + listing endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..middleware.rbac import require_role
from ..services import ingestion_service
from ..services.cache_service import invalidate_enforcement_caches

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.post("/reindex")
def reindex_vectors(
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("admin")),
):
    """Rebuild the vector index from scratch from all chunks in the DB."""
    from ..services.vector_store import vector_store
    count = vector_store.rebuild_from_db(db)
    return {"reindexed_chunks": count, **vector_store.stats()}


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
def get_source(
    source_id: str,
    chunk_limit: int = 50,
    rule_limit: int = 50,
    db: Session = Depends(get_db),
):
    src = db.query(models.Source).filter(models.Source.id == source_id).first()
    if src is None:
        raise HTTPException(status_code=404, detail="Source not found")
    base = _to_out(src, db).model_dump()

    chunk_rows = (
        db.query(models.SourceChunk)
        .filter(models.SourceChunk.source_id == src.id)
        .order_by(models.SourceChunk.chunk_index.asc())
        .limit(chunk_limit)
        .all()
    )
    chunks = [
        schemas.SourceChunkOut(
            id=c.id,
            chunk_index=c.chunk_index,
            text=(c.text or "")[:1500],
            page_number=c.page_number,
            url_section=c.url_section,
        )
        for c in chunk_rows
    ]

    rule_rows = (
        db.query(models.Rule)
        .filter(models.Rule.source_id == src.id)
        .order_by(models.Rule.created_at.desc())
        .limit(rule_limit)
        .all()
    )
    rules = [schemas.RuleOut.model_validate(r) for r in rule_rows]

    return schemas.SourceDetail(
        **base,
        raw_text_preview=(src.raw_text or "")[:4000],
        meta=src.meta,
        chunks=chunks,
        rules=rules,
    )


@router.get(
    "/{source_id}/versions", response_model=list[schemas.SourceVersionOut]
)
def list_source_versions(source_id: str, db: Session = Depends(get_db)):
    src = db.query(models.Source).filter(models.Source.id == source_id).first()
    if src is None:
        raise HTTPException(status_code=404, detail="Source not found")
    rows = (
        db.query(models.SourceVersion)
        .filter(models.SourceVersion.source_id == source_id)
        .order_by(models.SourceVersion.version.desc())
        .all()
    )
    return [
        schemas.SourceVersionOut(
            id=r.id,
            source_id=r.source_id,
            version=r.version,
            checksum=r.checksum,
            canonical_url=r.canonical_url,
            title=r.title,
            raw_text_preview=(r.raw_text or "")[:2000],
            status_at_capture=r.status_at_capture,
            captured_reason=r.captured_reason,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/{source_id}/check", response_model=schemas.LinkHealthOut)
def check_source(
    source_id: str,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("admin")),
):
    """Health-check the URL of a source (HEAD/GET) and update last_checked."""
    src = db.query(models.Source).filter(models.Source.id == source_id).first()
    if src is None:
        raise HTTPException(status_code=404, detail="Source not found")
    target = src.url or src.canonical_url
    if not target:
        raise HTTPException(
            status_code=400, detail="Source has no URL to health-check"
        )
    info = ingestion_service.link_health_check(target)
    src.last_checked = datetime.utcnow()
    if not info.get("ok"):
        src.error_message = info.get("error") or f"HTTP {info.get('status_code')}"
    db.commit()
    return schemas.LinkHealthOut(**info)


@router.post("/upload", response_model=schemas.IngestResult)
async def upload_source(
    file: UploadFile = File(...),
    state: Optional[str] = Form(default=None),
    tax_category: Optional[str] = Form(default=None),
    auto_extract: bool = Form(default=True),
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("admin")),
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
    invalidate_enforcement_caches()
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
    _role: str = Depends(require_role("admin")),
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
    invalidate_enforcement_caches()
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
    _role: str = Depends(require_role("admin")),
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
    invalidate_enforcement_caches()
    return schemas.IngestResult(
        source=_to_out(source, db),
        chunks_created=chunks,
        rules_created=rules,
        extraction_method=method,
    )


@router.delete("/{source_id}")
def delete_source(
    source_id: str,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("admin")),
):
    src = db.query(models.Source).filter(models.Source.id == source_id).first()
    if src is None:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(src)
    db.commit()
    try:
        from ..services.vector_store import vector_store
        vector_store.remove_source(source_id)
    except Exception:
        pass
    invalidate_enforcement_caches()
    return {"deleted": source_id}
