"""Ingestion service.

Responsible for turning raw inputs (PDFs, URLs, pasted text, file uploads)
into Source rows + SourceChunk rows. Rule extraction is delegated to
`extraction_service` and triggered here when the caller asks for
auto-extraction.

Status model on `Source`:
    pending → processing → processed
                        ↘ failed (with error_message)
                        ↘ skipped_duplicate (checksum matched existing)

The public `ingest_*` functions return (source, chunks, rules, method)
where `method` is one of:
    ingested | duplicate | updated | failed
"""

from __future__ import annotations

import hashlib
import io
import logging
import os
import uuid
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from ..utils.chunking import chunk_text
from . import extraction_service, versioning

logger = logging.getLogger(__name__)

# Conservative caps so a misbehaving source can't kill the prototype.
MAX_BYTES = 25 * 1024 * 1024  # 25MB
MAX_TEXT_CHARS = 1_500_000
DEFAULT_TIMEOUT = 20.0

USER_AGENT = (
    "Mozilla/5.0 (compatible; RulesIntelligenceBot/0.1; "
    "+https://example.com/bot)"
)


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


def fetch_url(url: str, timeout: float = DEFAULT_TIMEOUT) -> requests.Response:
    """Fetch a URL with our standard headers + timeout. Follows redirects."""
    headers = {"User-Agent": USER_AGENT}
    return requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)


def extract_url_payload(url: str, timeout: float = DEFAULT_TIMEOUT) -> dict:
    """Fetch a URL and return a dict with text + metadata.

    Keys: title, text, source_type ("webpage" or "pdf"), canonical_url,
    content_type, status_code, soup (BeautifulSoup or None).
    """
    r = fetch_url(url, timeout=timeout)
    r.raise_for_status()
    content_type = (r.headers.get("Content-Type") or "").lower()
    canonical = str(r.url) or url

    if "pdf" in content_type or url.lower().endswith(".pdf"):
        text = extract_pdf_text(r.content)
        title = os.path.basename(urlparse(canonical).path) or canonical
        return {
            "title": title,
            "text": text,
            "source_type": "pdf",
            "canonical_url": canonical,
            "content_type": content_type,
            "status_code": r.status_code,
            "soup": None,
        }

    soup = BeautifulSoup(r.text, "lxml")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "aside"]):
        tag.decompose()
    title = (
        soup.title.string.strip()
        if soup.title and soup.title.string
        else canonical
    )
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text(separator="\n", strip=True)
    return {
        "title": title,
        "text": text,
        "source_type": "webpage",
        "canonical_url": canonical,
        "content_type": content_type,
        "status_code": r.status_code,
        "soup": soup,
    }


# Backwards-compatible alias used elsewhere in the codebase / tests.
def extract_url_text(url: str, timeout: float = DEFAULT_TIMEOUT) -> tuple[str, str]:
    payload = extract_url_payload(url, timeout=timeout)
    return payload["title"], payload["text"]


# ---------------------------------------------------------------------------
# Link health + crawl helpers
# ---------------------------------------------------------------------------


def link_health_check(url: str, timeout: float = 10.0) -> dict:
    """Cheap GET-based health check (HEAD is too often blocked)."""
    headers = {"User-Agent": USER_AGENT}
    info: dict = {"url": url, "ok": False, "checked_at": datetime.utcnow().isoformat()}
    try:
        r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True, stream=True)
        info["status_code"] = r.status_code
        info["canonical_url"] = str(r.url)
        info["content_type"] = r.headers.get("Content-Type")
        info["ok"] = 200 <= r.status_code < 400
        if not info["ok"]:
            info["error"] = f"HTTP {r.status_code}"
        r.close()
    except requests.RequestException as exc:
        info["error"] = str(exc)
    return info


def crawl_links(
    start_url: str,
    *,
    depth: int = 1,
    max_pages: int = 10,
    same_host_only: bool = True,
) -> list[str]:
    """Breadth-first crawl from `start_url`, returning discovered URLs
    (including the start URL).

    Stays on the same host by default and is hard-capped at `max_pages`. The
    crawler only follows links on HTML pages — PDFs and other binary endpoints
    are returned as leaves.
    """
    if depth < 0:
        depth = 0
    start_host = urlparse(start_url).netloc
    seen: set[str] = set()
    out: list[str] = []
    queue: deque[tuple[str, int]] = deque([(start_url, 0)])

    while queue and len(out) < max_pages:
        url, level = queue.popleft()
        url = urldefrag(url).url
        if url in seen:
            continue
        seen.add(url)
        out.append(url)

        if level >= depth:
            continue

        try:
            payload = extract_url_payload(url)
        except Exception as exc:
            logger.warning("crawl: failed to fetch %s: %s", url, exc)
            continue

        soup = payload.get("soup")
        if soup is None:
            continue

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith(("mailto:", "javascript:", "tel:", "#")):
                continue
            absolute = urljoin(url, href)
            absolute = urldefrag(absolute).url
            parsed = urlparse(absolute)
            if parsed.scheme not in ("http", "https"):
                continue
            if same_host_only and parsed.netloc and parsed.netloc != start_host:
                continue
            if absolute in seen:
                continue
            queue.append((absolute, level + 1))

    return out


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


def find_source_by_url(db: Session, url: str) -> Optional[models.Source]:
    """Match by either url or canonical_url (after redirects)."""
    if not url:
        return None
    return (
        db.query(models.Source)
        .filter((models.Source.url == url) | (models.Source.canonical_url == url))
        .order_by(models.Source.created_at.desc())
        .first()
    )


def _persist_chunks(db: Session, source: models.Source, text: str) -> int:
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


def _replace_chunks(db: Session, source: models.Source, text: str) -> int:
    """Delete existing chunks for source, then re-chunk. Used on update."""
    db.query(models.SourceChunk).filter(
        models.SourceChunk.source_id == source.id
    ).delete(synchronize_session=False)
    db.flush()
    return _persist_chunks(db, source, text)


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


def _mark_failed(
    db: Session, source: Optional[models.Source], message: str
) -> None:
    if source is None:
        return
    source.status = "failed"
    source.error_message = message[:2000]
    source.last_checked = datetime.utcnow()
    db.commit()


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
        status="processing",
        checksum=checksum,
        last_checked=datetime.utcnow(),
    )
    db.add(source)
    db.flush()

    try:
        chunks = _persist_chunks(db, source, text)
        rules, method = _maybe_extract_rules(db, source, auto_extract=auto_extract)
        source.status = "processed"
        versioning.capture_source_version(db, source, reason="initial")
        db.commit()
        db.refresh(source)
        return source, chunks, rules, method
    except Exception as exc:
        _mark_failed(db, source, f"{type(exc).__name__}: {exc}")
        raise


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
    # Fetch outside of any source row so we don't strand a "processing" record
    # on a failed network call.
    payload = extract_url_payload(url)
    title = payload["title"]
    text = payload["text"]
    canonical = payload["canonical_url"]
    src_type = payload["source_type"]
    checksum = compute_checksum(text)
    now = datetime.utcnow()

    if skip_if_duplicate:
        # First try checksum (content-identical), then URL (re-fetched).
        dup_by_hash = find_source_by_checksum(db, checksum)
        if dup_by_hash is not None:
            dup_by_hash.last_checked = now
            db.commit()
            db.refresh(dup_by_hash)
            return dup_by_hash, 0, 0, "duplicate"

        existing = find_source_by_url(db, url) or find_source_by_url(db, canonical)
        if existing is not None and existing.checksum != checksum:
            # Same URL, content changed → snapshot the OLD state, then update
            # in place. We preserve rules so admin curation isn't wiped on
            # every re-fetch.
            versioning.capture_source_version(
                db, existing, reason="content_changed"
            )
            existing.raw_text = text[:MAX_TEXT_CHARS]
            existing.checksum = checksum
            existing.canonical_url = canonical
            existing.last_checked = now
            existing.last_changed = now
            existing.status = "processing"
            existing.error_message = None
            existing.source_type = src_type
            db.flush()
            try:
                chunks = _replace_chunks(db, existing, text)
                existing.status = "processed"
                db.commit()
                db.refresh(existing)
                return existing, chunks, 0, "updated"
            except Exception as exc:
                _mark_failed(db, existing, f"{type(exc).__name__}: {exc}")
                raise

    source = models.Source(
        source_type=src_type,
        name=name or title or url,
        url=url,
        canonical_url=canonical,
        state=state,
        tax_category=tax_category,
        raw_text=text[:MAX_TEXT_CHARS],
        status="processing",
        checksum=checksum,
        last_checked=now,
    )
    db.add(source)
    db.flush()
    try:
        chunks = _persist_chunks(db, source, text)
        rules, method = _maybe_extract_rules(db, source, auto_extract=auto_extract)
        source.status = "processed"
        versioning.capture_source_version(db, source, reason="initial")
        db.commit()
        db.refresh(source)
        return source, chunks, rules, method
    except Exception as exc:
        _mark_failed(db, source, f"{type(exc).__name__}: {exc}")
        raise


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
        status="processing",
        checksum=checksum,
        last_checked=datetime.utcnow(),
    )
    db.add(source)
    db.flush()

    try:
        chunks = _persist_chunks(db, source, text)
        rules, method = _maybe_extract_rules(db, source, auto_extract=auto_extract)
        source.status = "processed"
        versioning.capture_source_version(db, source, reason="initial")
        db.commit()
        db.refresh(source)
        return source, chunks, rules, method
    except Exception as exc:
        _mark_failed(db, source, f"{type(exc).__name__}: {exc}")
        raise
