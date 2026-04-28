"""SQLAlchemy ORM models.

Schema is inspired by the canonical rule model in the engineering brief
(Section 6). For the v1 prototype we flatten a few nested objects into JSON
fields and store list-typed properties as JSON for portability across
SQLite and Postgres.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


# ---------------------------------------------------------------------------
# Sources & chunks
# ---------------------------------------------------------------------------


class Source(Base):
    """A document, URL, or pasted text that rules are extracted from.

    Status transitions:
        pending → processing → processed
                            ↘ failed (with error_message)
                            ↘ skipped_duplicate (checksum matched existing)
    """

    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    source_type: Mapped[str] = mapped_column(String(32))  # pdf | url | text | manual | upload | webpage
    name: Mapped[str] = mapped_column(String(512))
    url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    canonical_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True, index=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tax_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    last_checked: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_changed: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    chunks: Mapped[list["SourceChunk"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )
    rules: Mapped[list["Rule"]] = relationship(back_populates="source")
    versions: Mapped[list["SourceVersion"]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan",
        order_by="SourceVersion.version.desc()",
    )


class SourceChunk(Base):
    """A chunk of source text used for retrieval."""

    __tablename__ = "source_chunks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    state: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tax_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    url_section: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    embedding_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    source: Mapped[Source] = relationship(back_populates="chunks")


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


class Rule(Base):
    """Canonical normalized rule.

    Field set is informed by Section 6 of the brief, focused on tax rules.
    `conditions`, `required_actions`, `required_forms`, `deadlines`,
    `exceptions` are stored as JSON arrays/objects so they survive across
    SQLite and Postgres without per-row tables.
    """

    __tablename__ = "rules"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    state: Mapped[str] = mapped_column(String(64), index=True)
    tax_category: Mapped[str] = mapped_column(String(64), index=True)
    rule_category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    rule_title: Mapped[str] = mapped_column(String(512))
    rule_summary: Mapped[str] = mapped_column(Text)
    detailed_rule: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    conditions: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    required_actions: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    required_forms: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    deadlines: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    exceptions: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)

    source_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL"), nullable=True
    )
    source_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    source_document_name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    source_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    effective_date: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    review_status: Mapped[str] = mapped_column(String(32), default="draft")
    # draft | auto_validated | needs_review | approved | published | rejected

    extraction_method: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    supersedes_rule_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("rules.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    source: Mapped[Optional[Source]] = relationship(back_populates="rules")
    review_events: Mapped[list["ReviewEvent"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )
    versions: Mapped[list["RuleVersion"]] = relationship(
        back_populates="rule",
        cascade="all, delete-orphan",
        order_by="RuleVersion.version.desc()",
    )


# ---------------------------------------------------------------------------
# Q&A history
# ---------------------------------------------------------------------------


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    text: Mapped[str] = mapped_column(Text)
    state: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tax_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    answers: Mapped[list["Answer"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    answer_text: Mapped[str] = mapped_column(Text)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    citations: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    rules_used: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    method: Mapped[str] = mapped_column(String(32), default="fallback")  # llm | fallback
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    question: Mapped[Question] = relationship(back_populates="answers")


# ---------------------------------------------------------------------------
# Review trail
# ---------------------------------------------------------------------------


class ReviewEvent(Base):
    __tablename__ = "review_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    rule_id: Mapped[str] = mapped_column(ForeignKey("rules.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String(32))  # edit | approve | reject | publish
    actor: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    diff: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    rule: Mapped[Rule] = relationship(back_populates="review_events")


# ---------------------------------------------------------------------------
# Ingestion runs (history / observability)
# ---------------------------------------------------------------------------


class IngestionRun(Base):
    """One ingestion invocation — manual single-source, batch yaml, or scheduled.

    Each run has many `IngestionRunItem`s, one per source attempted. Counters
    (`total`, `ingested`, `duplicates`, `errors`) are denormalized for cheap
    listing.
    """

    __tablename__ = "ingestion_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    kind: Mapped[str] = mapped_column(String(32))  # single | yaml | upload | text | crawl | monitor
    status: Mapped[str] = mapped_column(String(32), default="running")  # running | completed | failed
    triggered_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    only_state: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    only_tax_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    total: Mapped[int] = mapped_column(Integer, default=0)
    ingested: Mapped[int] = mapped_column(Integer, default=0)
    duplicates: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[int] = mapped_column(Integer, default=0)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    items: Mapped[list["IngestionRunItem"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class IngestionRunItem(Base):
    """One source attempted inside an ingestion run."""

    __tablename__ = "ingestion_run_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("ingestion_runs.id", ondelete="CASCADE"))
    source_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL"), nullable=True
    )

    name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tax_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    status: Mapped[str] = mapped_column(String(32))  # ingested | duplicate | failed | crawled
    chunks_created: Mapped[int] = mapped_column(Integer, default=0)
    rules_created: Mapped[int] = mapped_column(Integer, default=0)
    extraction_method: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    run: Mapped[IngestionRun] = relationship(back_populates="items")


# ---------------------------------------------------------------------------
# Versioning & lineage
# ---------------------------------------------------------------------------


class SourceVersion(Base):
    """Immutable snapshot of a `Source` at a point in time.

    A new version is captured whenever the underlying content changes
    (checksum diff on re-fetch). Version 1 is captured at first ingestion
    so every source has at least one version row.
    """

    __tablename__ = "source_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    canonical_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status_at_capture: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    captured_reason: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # initial | content_changed | manual

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    source: Mapped[Source] = relationship(back_populates="versions")


class RuleVersion(Base):
    """Immutable snapshot of a `Rule` whenever it is edited or re-extracted.

    Stores both the previous and new field-level state plus the diff so the
    audit trail can be reconstructed without joining back to the live row.
    """

    __tablename__ = "rule_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    rule_id: Mapped[str] = mapped_column(
        ForeignKey("rules.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)

    previous_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    new_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    changed_fields: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)

    extraction_method: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_version_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("source_versions.id", ondelete="SET NULL"), nullable=True
    )
    actor: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    captured_reason: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # initial | edit | review_action | re_extract | source_change

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    rule: Mapped[Rule] = relationship(back_populates="versions")
