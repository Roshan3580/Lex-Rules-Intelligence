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
    canonical_url: Optional[str] = None
    status: str  # pending | processing | processed | failed | skipped_duplicate
    error_message: Optional[str] = None
    checksum: Optional[str] = None
    last_checked: Optional[datetime] = None
    last_changed: Optional[datetime] = None
    current_version: int = 1
    created_at: datetime
    updated_at: datetime
    chunk_count: int = 0
    rule_count: int = 0

    class Config:
        from_attributes = True


class SourceChunkOut(BaseModel):
    id: str
    chunk_index: int
    text: str
    page_number: Optional[int] = None
    url_section: Optional[str] = None

    class Config:
        from_attributes = True


class SourceDetail(SourceOut):
    raw_text_preview: Optional[str] = None
    meta: Optional[dict[str, Any]] = None
    chunks: list[SourceChunkOut] = []
    rules: list["RuleOut"] = []


class LinkHealthOut(BaseModel):
    url: str
    ok: bool
    status_code: Optional[int] = None
    canonical_url: Optional[str] = None
    content_type: Optional[str] = None
    error: Optional[str] = None
    checked_at: str


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
    workflow_stage: Optional[str] = None
    operating_scenario: Optional[str] = None
    condition_logic: Optional[str] = None
    submission_method: Optional[str] = None
    rule_title: str
    rule_summary: str
    detailed_rule: Optional[str] = None
    conditions: Optional[list[str]] = None
    required_actions: Optional[list[str]] = None
    required_forms: Optional[list[str]] = None
    required_documentation: Optional[list[str]] = None
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
    rule_category: Optional[str] = None
    workflow_stage: Optional[str] = None
    operating_scenario: Optional[str] = None
    condition_logic: Optional[str] = None
    submission_method: Optional[str] = None
    rule_title: Optional[str] = None
    rule_summary: Optional[str] = None
    detailed_rule: Optional[str] = None
    conditions: Optional[list[str]] = None
    required_actions: Optional[list[str]] = None
    required_forms: Optional[list[str]] = None
    required_documentation: Optional[list[str]] = None
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
    lineage: Optional[dict[str, Any]] = None
    validation_errors: Optional[list[str]] = None
    validation_warnings: Optional[list[str]] = None
    current_version: int = 1
    supersedes_rule_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ValidationOut(BaseModel):
    valid: bool
    errors: list[str] = []
    warnings: list[str] = []
    suggested_review_status: str
    adjusted_confidence: float


class ConflictOut(BaseModel):
    duplicate_of: Optional[str] = None
    conflicting_rule_ids: list[str] = []
    notes: list[str] = []


class RuleAssessmentOut(BaseModel):
    rule_id: str
    validation: ValidationOut
    conflicts: ConflictOut


class RuleVersionOut(BaseModel):
    id: str
    rule_id: str
    version: int
    previous_data: Optional[dict[str, Any]] = None
    new_data: Optional[dict[str, Any]] = None
    changed_fields: Optional[list[str]] = None
    extraction_method: Optional[str] = None
    source_version_id: Optional[str] = None
    actor: Optional[str] = None
    notes: Optional[str] = None
    captured_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SourceVersionOut(BaseModel):
    id: str
    source_id: str
    version: int
    checksum: Optional[str] = None
    canonical_url: Optional[str] = None
    title: Optional[str] = None
    raw_text_preview: Optional[str] = None
    status_at_capture: Optional[str] = None
    captured_reason: Optional[str] = None
    created_at: datetime

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
    workflow_stage: Optional[str] = None
    operating_scenario: Optional[str] = None
    statuses: Optional[list[str]] = None
    top_k: int = 6


class AnswerOut(BaseModel):
    id: str
    question_id: str
    question: str
    answer: str
    confidence_score: float
    citations: list[Citation]
    rules_used: list[RuleOut]
    chunks_used: list[str] = []
    source_versions_used: list[str] = []
    safety_flags: list[str] = []
    method: str
    retrieval_mode: str = "lexical"
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
    embedding_provider: str = "none"
    embedding_enabled: bool = False
    vector_backend: str = "none"
    vector_enabled: bool = False
    vector_index_size: int = 0


# ---------------------------------------------------------------------------
# Spec-shaped DTOs (POST /api/query, /api/states, /api/ingest/*)
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    """Spec-shaped request: matches the contract in the engineering brief."""

    question: str = Field(..., min_length=1)
    state: Optional[str] = None
    tax_type: Optional[str] = None  # synonym of tax_category
    workflow_stage: Optional[str] = None
    operating_scenario: Optional[str] = None
    statuses: Optional[list[str]] = None
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
    retrieval_mode: str = "lexical"  # lexical | hybrid
    rules_used: list["RuleOut"]
    chunks_used: list[str] = []
    source_versions_used: list[str] = []
    safety_flags: list[str] = []
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
    crawl_depth: int = 0  # 0 = just the URL; >0 = follow same-host links
    crawl_max_pages: int = 5


class IngestRunRequest(BaseModel):
    only_state: Optional[str] = None
    only_tax_type: Optional[str] = None
    auto_extract: bool = True


class IngestRunItem(BaseModel):
    """Per-source row inside an ingestion run."""

    name: Optional[str] = None
    url: Optional[str] = None
    state: Optional[str] = None
    tax_type: Optional[str] = None
    source_id: Optional[str] = None
    source_type: Optional[str] = None
    status: str  # ingested | duplicate | failed | updated | crawled
    chunks_created: int = 0
    rules_created: int = 0
    extraction_method: Optional[str] = None
    error: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None


class IngestRunResult(BaseModel):
    """Synchronous response shape for /api/ingest/run and /api/ingest/source."""

    total: int
    ingested: int
    duplicates: int
    errors: int
    items: list[IngestRunItem]
    run_id: Optional[str] = None


class IngestionRunOut(BaseModel):
    """Listing row for GET /api/ingest/runs."""

    id: str
    kind: str
    status: str
    triggered_by: Optional[str] = None
    only_state: Optional[str] = None
    only_tax_type: Optional[str] = None
    notes: Optional[str] = None
    total: int
    ingested: int
    duplicates: int
    errors: int
    started_at: datetime
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class IngestionRunDetail(IngestionRunOut):
    items: list[IngestRunItem] = []


class AdminRoleOut(BaseModel):
    """Placeholder RBAC role until real identity is wired."""

    id: str
    label: str
    description: str


class AdminTaxonomyOut(BaseModel):
    states: list[StateOut]
    tax_categories: list[str]
    workflow_stages: list[str]
    source_types: list[str]
    review_statuses: list[str]


class AdminSummaryOut(BaseModel):
    total_sources: int
    total_rules: int
    published_rules: int
    rules_in_review: int
    failed_sources: int
    avg_confidence: float
    extraction_breakdown: dict[str, int] = {}
    last_ingestion_run: Optional[dict[str, Any]] = None
    llm_enabled: bool
    retrieval_mode: str = "lexical"
    embedding_provider: str = "none"
    vector_index_size: int = 0


class ReviewAuditEventOut(BaseModel):
    """One row in the global review audit feed."""

    id: str
    rule_id: str
    rule_title: str
    state: str
    tax_category: str
    action: str
    actor: Optional[str] = None
    notes: Optional[str] = None
    diff: Optional[dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Workflow guidance (Phase 7)
# ---------------------------------------------------------------------------


class WorkflowChecklistItem(BaseModel):
    key: str
    label: str
    checked: Optional[bool] = None


class WorkflowRuleSummary(BaseModel):
    id: str
    rule_title: str
    rule_summary: Optional[str] = None
    tax_category: Optional[str] = None
    state: Optional[str] = None
    workflow_stage: Optional[str] = None
    required_forms: list[str] = []
    required_documentation: list[str] = []
    deadlines: list[str] = []
    exceptions: list[str] = []
    submission_method: Optional[str] = None
    source_url: Optional[str] = None
    confidence_score: Optional[float] = None
    review_status: Optional[str] = None


class WorkflowStep(BaseModel):
    key: str
    title: str
    description: Optional[str] = None
    workflow_stage: Optional[str] = None
    checklist: list[WorkflowChecklistItem] = []
    rules: list[WorkflowRuleSummary] = []
    rule_count: Optional[int] = None
    aggregated_forms: list[str] = []
    aggregated_documents: list[str] = []
    aggregated_deadlines: list[str] = []
    aggregated_validations: list[str] = []
    status: Optional[str] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None


class WorkflowTemplateOut(BaseModel):
    id: str
    key: str
    title: str
    description: Optional[str] = None
    state: Optional[str] = None
    tax_category: Optional[str] = None
    workflow_stage: Optional[str] = None
    is_builtin: bool = True
    steps: list[WorkflowStep] = []
    required_rule_filters: list[dict[str, Any]] = []
    created_at: datetime
    updated_at: datetime


class CaseWorkflowEventOut(BaseModel):
    id: str
    action: str
    step_key: Optional[str] = None
    actor: Optional[str] = None
    notes: Optional[str] = None
    payload: Optional[dict[str, Any]] = None
    created_at: datetime


class CaseWorkflowOut(BaseModel):
    id: str
    case_id: str
    title: Optional[str] = None
    org: Optional[str] = None
    template_id: Optional[str] = None
    state: Optional[str] = None
    tax_category: Optional[str] = None
    current_stage: Optional[str] = None
    status: str
    steps: list[WorkflowStep] = []
    completed_steps: list[str] = []
    step_count: int = 0
    completed_count: int = 0
    progress: float = 0.0
    events: list[CaseWorkflowEventOut] = []
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class CreateCaseRequest(BaseModel):
    state: Optional[str] = None
    tax_category: Optional[str] = None
    title: Optional[str] = None
    org: Optional[str] = None
    template_id: Optional[str] = None
    case_id: Optional[str] = None
    actor: Optional[str] = None


class UpdateStepRequest(BaseModel):
    step_key: str
    completed: Optional[bool] = None
    notes: Optional[str] = None
    actor: Optional[str] = None


SourceDetail.model_rebuild()
QueryResponse.model_rebuild()
