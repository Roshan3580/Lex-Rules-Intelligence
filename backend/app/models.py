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
    """A document, URL, or pasted text that rules are extracted from."""

    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    source_type: Mapped[str] = mapped_column(String(32))  # pdf | url | text | upload
    name: Mapped[str] = mapped_column(String(512))
    url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tax_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ingested")
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    last_checked: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    chunks: Mapped[list["SourceChunk"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )
    rules: Mapped[list["Rule"]] = relationship(back_populates="source")


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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    source: Mapped[Optional[Source]] = relationship(back_populates="rules")
    review_events: Mapped[list["ReviewEvent"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
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
