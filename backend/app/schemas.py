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
