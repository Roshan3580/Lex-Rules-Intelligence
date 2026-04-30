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
# Governance (Brief §6, §9.1) — canonical dimensions
# ---------------------------------------------------------------------------


class Jurisdiction(Base):
    """Geographic / legal jurisdiction (state, locality in future)."""

    __tablename__ = "jurisdictions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    parent_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("jurisdictions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class ProgramVariantDef(Base):
    """Named program + variant (e.g. annual vs monthly) for rule scoping."""

    __tablename__ = "program_variants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    key_slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(255))
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class RejectionReason(Base):
    """Operational rejection code catalog (maps to filings / portals)."""

    __tablename__ = "rejection_reasons"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(512))
    category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    rule_links: Mapped[list["RuleRejectionLink"]] = relationship(
        back_populates="reason", cascade="all, delete-orphan"
    )


class RuleRejectionLink(Base):
    """Associates rules with catalog rejection codes (Brief §4.4)."""

    __tablename__ = "rule_rejection_links"

    rule_id: Mapped[str] = mapped_column(
        ForeignKey("rules.id", ondelete="CASCADE"), primary_key=True
    )
    rejection_reason_id: Mapped[str] = mapped_column(
        ForeignKey("rejection_reasons.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    rule: Mapped["Rule"] = relationship(back_populates="rejection_links")
    reason: Mapped["RejectionReason"] = relationship(back_populates="rule_links")


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
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)

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

    workflow_stage: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # intake | verification | documentation | submission | resolution | other
    operating_scenario: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    condition_logic: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submission_method: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    # online_portal | mail | in_person | eft | other
    program_variant: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    # Brief §6 — program_variant JSON keeps rapid iteration; optional FK canonicalizes.
    program_variant_ref_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("program_variants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    jurisdiction_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("jurisdictions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)

    # Structured brief fields (JSON); legacy string columns retained where present.
    operating_scenario_json: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    filing_timing: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    required_actions_structured: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSON, nullable=True
    )
    submission_portal_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    submission_endpoint_urls: Mapped[Optional[list[str]]] = mapped_column(
        JSON, nullable=True
    )
    portal_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    conditions: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    required_actions: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    required_forms: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    required_documentation: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    deadlines: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    exceptions: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)

    source_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL"), nullable=True
    )
    source_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    source_document_name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    source_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    effective_date: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    effective_date_end: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    review_status: Mapped[str] = mapped_column(String(32), default="draft")
    # draft | auto_validated | needs_review | approved | published | rejected

    extraction_method: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    lineage: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    validation_errors: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    validation_warnings: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    supersedes_rule_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("rules.id", ondelete="SET NULL"), nullable=True
    )
    superseded_by_rule_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("rules.id", ondelete="SET NULL"), nullable=True, index=True
    )
    superseded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    extraction_run_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("ingestion_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    extractor_model_version: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    extractor_prompt_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    reviewer_user_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    source: Mapped[Optional[Source]] = relationship(back_populates="rules")
    jurisdiction: Mapped[Optional["Jurisdiction"]] = relationship()
    program_variant_ref: Mapped[Optional["ProgramVariantDef"]] = relationship()
    extraction_run: Mapped[Optional["IngestionRun"]] = relationship()
    rejection_links: Mapped[list["RuleRejectionLink"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )
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
    chunks_used: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    source_versions_used: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    retrieval_mode: Mapped[str] = mapped_column(String(32), default="lexical")
    safety_flags: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
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
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
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
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
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


# ---------------------------------------------------------------------------
# Outcome / rejection feedback (enforcement loop)
# ---------------------------------------------------------------------------


class OutcomeEvent(Base):
    """Structured operational outcome for coverage analytics (brief §4.4)."""

    __tablename__ = "outcome_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    submission_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    state: Mapped[str] = mapped_column(String(64), index=True)
    tax_category: Mapped[str] = mapped_column(String(64), index=True)
    workflow_stage: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    rejection_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    rejection_reason: Mapped[str] = mapped_column(Text)
    normalized_root_cause: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    matched_rule_ids: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    coverage_status: Mapped[str] = mapped_column(
        String(64), index=True
    )  # prevented_by_existing_rule | rule_existed_but_not_enforced | missing_rule | unclear

    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


# ---------------------------------------------------------------------------
# Workflow guidance (Phase 7)
# ---------------------------------------------------------------------------


class WorkflowTemplate(Base):
    """Reusable workflow definition for a (state, tax_category) pair.

    A template's `steps` is a list of stage dicts:
        {
            "key": "intake",
            "title": "Intake",
            "description": "...",
            "workflow_stage": "intake",
            "checklist": [
                {"key": "register", "label": "Register with state authority"},
                ...
            ]
        }

    `required_rule_filters` is an optional list of rule filters the
    runtime resolver uses to attach live, source-backed rules to each
    stage at case-creation time. Example:
        [{"workflow_stage": "intake"}, {"workflow_stage": "verification"}]
    """

    __tablename__ = "workflow_templates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    key: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    state: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    tax_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    workflow_stage: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    required_rule_filters: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSON, nullable=True
    )

    is_builtin: Mapped[bool] = mapped_column(default=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    cases: Mapped[list["CaseWorkflow"]] = relationship(
        back_populates="template", cascade="all, delete-orphan"
    )


class CaseWorkflow(Base):
    """Per-case instantiation of a `WorkflowTemplate`.

    `steps` is a snapshot of the template's steps at creation time, with
    each step augmented with runtime fields (`status`, `completed_at`,
    `notes`, `attached_rule_ids`). Mutations should go through the
    workflows service so the audit trail is kept consistent.
    """

    __tablename__ = "case_workflows"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(64), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    org: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    template_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("workflow_templates.id", ondelete="SET NULL"), nullable=True
    )

    state: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    tax_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    current_stage: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    # active | completed | abandoned

    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    completed_steps: Mapped[list[str]] = mapped_column(JSON, default=list)

    validation_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    template: Mapped[Optional[WorkflowTemplate]] = relationship(back_populates="cases")
    events: Mapped[list["CaseWorkflowEvent"]] = relationship(
        back_populates="case", cascade="all, delete-orphan",
        order_by="CaseWorkflowEvent.created_at.asc()",
    )


class CaseWorkflowEvent(Base):
    """Append-only audit trail for case progress.

    Captures actor, action (start/complete_step/uncomplete_step/note/finish),
    and a payload snapshot so changes are reversible / inspectable later.
    """

    __tablename__ = "case_workflow_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    case_workflow_id: Mapped[str] = mapped_column(
        ForeignKey("case_workflows.id", ondelete="CASCADE"), index=True
    )
    action: Mapped[str] = mapped_column(String(64))
    step_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    actor: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    case: Mapped[CaseWorkflow] = relationship(back_populates="events")


# ---------------------------------------------------------------------------
# Platform (webhooks, audit, §4.7)
# ---------------------------------------------------------------------------


class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    url: Mapped[str] = mapped_column(String(1024))
    events: Mapped[list[str]] = mapped_column(JSON, default=list)
    secret_hint: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    signing_secret: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    delivery_attempts: Mapped[list["WebhookDeliveryAttempt"]] = relationship(
        back_populates="subscription",
        cascade="all, delete-orphan",
    )


class WebhookDeliveryAttempt(Base):
    """Outbound webhook delivery audit + retry state."""

    __tablename__ = "webhook_delivery_attempts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    subscription_id: Mapped[str] = mapped_column(
        ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(
        String(32), default="pending", index=True
    )  # pending | success | failed
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_body_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )

    subscription: Mapped["WebhookSubscription"] = relationship(
        back_populates="delivery_attempts"
    )


class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    resource_type: Mapped[str] = mapped_column(String(64), index=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    actor: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    detail: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)
