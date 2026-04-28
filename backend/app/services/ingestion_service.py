"""Ingestion service.

Responsible for turning raw inputs (PDFs, URLs, pasted text, file uploads)
into Source rows + SourceChunk rows. Rule extraction is delegated to
`extraction_service` and triggered here when the caller asks for
auto-extraction.
"""

from __future__ import annotations

import hashlib
import io
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from ..utils.chunking import chunk_text
from . import extraction_service

logger = logging.getLogger(__name__)

# Conservative caps so a misbehaving source can't kill the prototype.
MAX_BYTES = 25 * 1024 * 1024  # 25MB
MAX_TEXT_CHARS = 1_500_000


# ---------------------------------------------------------------------------
# Text extractors
# ---------------------------------------------------------------------------


def extract_pdf_text(data: bytes) -> str:
    """Extract text from a PDF byte stream.

    We try PyMuPDF first (fast, decent layout) and fall back to pdfplumber
    if it fails on a particular file.
    """
    try:
        import fitz  # PyMuPDF

        out: list[str] = []
        with fitz.open(stream=data, filetype="pdf") as doc:
            for page in doc:
                out.append(page.get_text("text"))
        text = "\n".join(out).strip()
        if text:
            return text
    except Exception as exc:  # pragma: no cover - fallback path
        logger.warning("PyMuPDF failed, falling back to pdfplumber: %s", exc)

    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages).strip()
    except Exception as exc:
        logger.error("pdfplumber also failed: %s", exc)
        return ""


def extract_url_text(url: str, timeout: float = 20.0) -> tuple[str, str]:
    """Fetch a URL and return (title, text).

    For HTML we use BeautifulSoup to strip nav/footer/script. For
    PDF-content-type we delegate to extract_pdf_text.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; RulesIntelligenceBot/0.1; "
            "+https://example.com/bot)"
        )
    }
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    content_type = r.headers.get("Content-Type", "").lower()

    if "pdf" in content_type or url.lower().endswith(".pdf"):
        text = extract_pdf_text(r.content)
        title = os.path.basename(url) or url
        return title, text

    soup = BeautifulSoup(r.text, "lxml")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "aside"]):
        tag.decompose()
    title = (soup.title.string.strip() if soup.title and soup.title.string else url)
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text(separator="\n", strip=True)
    return title, text


# ---------------------------------------------------------------------------
# Source creation primitives
# ---------------------------------------------------------------------------


def compute_checksum(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()


def find_source_by_checksum(db: Session, checksum: str) -> Optional[models.Source]:
    return (
        db.query(models.Source)
        .filter(models.Source.checksum == checksum)
        .first()
    )


def _persist_chunks(
    db: Session,
    source: models.Source,
    text: str,
) -> int:
    """Chunk text and persist as SourceChunk rows. Returns count."""
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS]
    chunks = chunk_text(text)
    for i, c in enumerate(chunks):
        db.add(
            models.SourceChunk(
                source_id=source.id,
                chunk_index=i,
                text=c,
                state=source.state,
                tax_category=source.tax_category,
            )
        )
    db.flush()
    return len(chunks)


def _maybe_extract_rules(
    db: Session,
    source: models.Source,
    *,
    auto_extract: bool,
) -> tuple[int, str]:
    if not auto_extract:
        return 0, "skipped"
    created, method = extraction_service.extract_rules_for_source(db, source)
    return created, method


# ---------------------------------------------------------------------------
# Public ingestion API
# ---------------------------------------------------------------------------


def ingest_text(
    db: Session,
    *,
    name: str,
    text: str,
    state: Optional[str] = None,
    tax_category: Optional[str] = None,
    auto_extract: bool = True,
    skip_if_duplicate: bool = False,
    url: Optional[str] = None,
    source_type: str = "text",
) -> tuple[models.Source, int, int, str]:
    checksum = compute_checksum(text)
    if skip_if_duplicate:
        existing = find_source_by_checksum(db, checksum)
        if existing is not None:
            existing.last_checked = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing, 0, 0, "duplicate"

    source = models.Source(
        source_type=source_type,
        name=name,
        url=url,
        state=state,
        tax_category=tax_category,
        raw_text=text[:MAX_TEXT_CHARS],
        status="ingested",
        checksum=checksum,
        last_checked=datetime.utcnow(),
    )
    db.add(source)
    db.flush()

    chunks = _persist_chunks(db, source, text)
    rules, method = _maybe_extract_rules(db, source, auto_extract=auto_extract)
    db.commit()
    db.refresh(source)
    return source, chunks, rules, method


def ingest_url(
    db: Session,
    *,
    url: str,
    state: Optional[str] = None,
    tax_category: Optional[str] = None,
    name: Optional[str] = None,
    auto_extract: bool = True,
    skip_if_duplicate: bool = True,
) -> tuple[models.Source, int, int, str]:
    title, text = extract_url_text(url)
    checksum = compute_checksum(text)

    if skip_if_duplicate:
        existing = find_source_by_checksum(db, checksum)
        if existing is not None:
            existing.last_checked = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing, 0, 0, "duplicate"

    source = models.Source(
        source_type="url",
        name=name or title or url,
        url=url,
        state=state,
        tax_category=tax_category,
        raw_text=text[:MAX_TEXT_CHARS],
        status="ingested",
        checksum=checksum,
        last_checked=datetime.utcnow(),
    )
    db.add(source)
    db.flush()

    chunks = _persist_chunks(db, source, text)
    rules, method = _maybe_extract_rules(db, source, auto_extract=auto_extract)
    db.commit()
    db.refresh(source)
    return source, chunks, rules, method


def ingest_upload(
    db: Session,
    *,
    filename: str,
    data: bytes,
    state: Optional[str] = None,
    tax_category: Optional[str] = None,
    auto_extract: bool = True,
    skip_if_duplicate: bool = True,
) -> tuple[models.Source, int, int, str]:
    if len(data) > MAX_BYTES:
        raise ValueError(f"File too large: {len(data)} bytes (max {MAX_BYTES})")

    safe_name = f"{uuid.uuid4().hex[:8]}_{Path(filename).name}"
    file_path = settings.upload_path / safe_name
    file_path.write_bytes(data)

    lower = filename.lower()
    if lower.endswith(".pdf"):
        text = extract_pdf_text(data)
        source_type = "pdf"
    elif lower.endswith((".txt", ".md", ".html", ".htm")):
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            text = ""
        if lower.endswith((".html", ".htm")):
            soup = BeautifulSoup(text, "lxml")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
        source_type = "upload"
    else:
        try:
            text = data.decode("utf-8")
            source_type = "upload"
        except UnicodeDecodeError:
            text = extract_pdf_text(data)
            source_type = "pdf"

    checksum = compute_checksum(text)
    if skip_if_duplicate:
        existing = find_source_by_checksum(db, checksum)
        if existing is not None:
            existing.last_checked = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing, 0, 0, "duplicate"

    source = models.Source(
        source_type=source_type,
        name=filename,
        file_path=str(file_path),
        state=state,
        tax_category=tax_category,
        raw_text=text[:MAX_TEXT_CHARS],
        status="ingested",
        checksum=checksum,
        last_checked=datetime.utcnow(),
    )
    db.add(source)
    db.flush()

    chunks = _persist_chunks(db, source, text)
    rules, method = _maybe_extract_rules(db, source, auto_extract=auto_extract)
    db.commit()
    db.refresh(source)
    return source, chunks, rules, method
