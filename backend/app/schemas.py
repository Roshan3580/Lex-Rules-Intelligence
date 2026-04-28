"""Pydantic schemas (request / response DTOs)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TAX_CATEGORIES = [
    "sales_tax",
    "payroll_tax",
    "corporate_tax",
    "income_tax",
    "withholding",
    "franchise_tax",
    "other",
]

REVIEW_STATUSES = [
    "draft",
    "auto_validated",
    "needs_review",
    "approved",
    "published",
    "rejected",
]


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------


class SourceBase(BaseModel):
    name: str
    source_type: str
    url: Optional[str] = None
    state: Optional[str] = None
    tax_category: Optional[str] = None


class SourceOut(SourceBase):
    id: str
    file_path: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    chunk_count: int = 0
    rule_count: int = 0

    class Config:
        from_attributes = True


class SourceDetail(SourceOut):
    raw_text_preview: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


class IngestUrlRequest(BaseModel):
    url: str
    state: Optional[str] = None
    tax_category: Optional[str] = None
    name: Optional[str] = None
    auto_extract: bool = True


class IngestTextRequest(BaseModel):
    name: str
    text: str
    state: Optional[str] = None
    tax_category: Optional[str] = None
    auto_extract: bool = True


class IngestResult(BaseModel):
    source: SourceOut
    chunks_created: int
    rules_created: int
    extraction_method: str


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


class RuleBase(BaseModel):
    state: str
    tax_category: str
    rule_category: Optional[str] = None
    rule_title: str
    rule_summary: str
    detailed_rule: Optional[str] = None
    conditions: Optional[list[str]] = None
    required_actions: Optional[list[str]] = None
    required_forms: Optional[list[str]] = None
    deadlines: Optional[list[str]] = None
    exceptions: Optional[list[str]] = None
    source_url: Optional[str] = None
    source_document_name: Optional[str] = None
    source_snippet: Optional[str] = None
    effective_date: Optional[str] = None
    confidence_score: float = 0.0
    review_status: str = "draft"


class RuleCreate(RuleBase):
    source_id: Optional[str] = None
    extraction_method: Optional[str] = None


class RuleUpdate(BaseModel):
    state: Optional[str] = None
    tax_category: Optional[str] = None
    rule_title: Optional[str] = None
    rule_summary: Optional[str] = None
    detailed_rule: Optional[str] = None
    conditions: Optional[list[str]] = None
    required_actions: Optional[list[str]] = None
    required_forms: Optional[list[str]] = None
    deadlines: Optional[list[str]] = None
    exceptions: Optional[list[str]] = None
    source_url: Optional[str] = None
    source_document_name: Optional[str] = None
    source_snippet: Optional[str] = None
    effective_date: Optional[str] = None
    confidence_score: Optional[float] = None
    review_status: Optional[str] = None


class RuleOut(RuleBase):
    id: str
    source_id: Optional[str] = None
    extraction_method: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Q&A
# ---------------------------------------------------------------------------


class Citation(BaseModel):
    rule_id: Optional[str] = None
    source_id: Optional[str] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    snippet: str
    state: Optional[str] = None
    tax_category: Optional[str] = None
    relevance: float = 0.0


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    state: Optional[str] = None
    tax_category: Optional[str] = None
    top_k: int = 6


class AnswerOut(BaseModel):
    id: str
    question_id: str
    question: str
    answer: str
    confidence_score: float
    citations: list[Citation]
    rules_used: list[RuleOut]
    method: str
    state: Optional[str] = None
    tax_category: Optional[str] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------


class ReviewActionRequest(BaseModel):
    action: str  # approve | reject | publish | needs_review | edit
    actor: Optional[str] = "admin"
    notes: Optional[str] = None


class ReviewEventOut(BaseModel):
    id: str
    rule_id: str
    action: str
    actor: Optional[str]
    notes: Optional[str]
    diff: Optional[dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------


class HealthOut(BaseModel):
    status: str
    llm_enabled: bool
    database: str
    demo_mode: bool = False


# ---------------------------------------------------------------------------
# Spec-shaped DTOs (POST /api/query, /api/states, /api/ingest/*)
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    """Spec-shaped request: matches the contract in the engineering brief."""

    question: str = Field(..., min_length=1)
    state: Optional[str] = None
    tax_type: Optional[str] = None  # synonym of tax_category
    top_k: int = 6


class QuerySource(BaseModel):
    title: str
    url: Optional[str] = None
    snippet: str
    document_type: str  # webpage | pdf | manual | form | bulletin | rule
    last_checked: Optional[datetime] = None
    state: Optional[str] = None
    tax_type: Optional[str] = None
    relevance: float = 0.0


class QueryResponse(BaseModel):
    """Spec-shaped Q&A response."""

    answer: str
    state: Optional[str] = None
    tax_type: Optional[str] = None
    sources: list[QuerySource]
    confidence: float
    method: str  # llm | fallback
    rules_used: list["RuleOut"]
    question_id: str
    answered_at: datetime


class StateOut(BaseModel):
    name: str
    abbreviation: str


class IngestSourceRequest(BaseModel):
    """POST /api/ingest/source — unified URL/manual ingestion entry point."""

    source_type: str = Field(default="webpage")  # webpage | url | manual | text | pdf
    url: Optional[str] = None
    title: Optional[str] = None
    text: Optional[str] = None
    state: Optional[str] = None
    tax_type: Optional[str] = None
    auto_extract: bool = True


class IngestRunRequest(BaseModel):
    only_state: Optional[str] = None
    only_tax_type: Optional[str] = None
    auto_extract: bool = True


class IngestRunItem(BaseModel):
    name: str
    url: Optional[str] = None
    state: Optional[str] = None
    tax_type: Optional[str] = None
    status: str
    chunks_created: int = 0
    rules_created: int = 0
    extraction_method: Optional[str] = None
    error: Optional[str] = None


class IngestRunResult(BaseModel):
    total: int
    ingested: int
    duplicates: int
    errors: int
    items: list[IngestRunItem]
