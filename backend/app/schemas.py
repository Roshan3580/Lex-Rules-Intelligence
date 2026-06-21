"""Pydantic schemas (request / response DTOs)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TAX_CATEGORIES = [
    "general_tax",  # jurisdiction-wide portal / index entry
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
    program_variant: Optional[dict[str, Any]] = None
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
    effective_date_end: Optional[str] = None
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
    program_variant: Optional[dict[str, Any]] = None
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
    effective_date_end: Optional[str] = None
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
    """Spec-shaped request matching the public API contract."""

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


class MonitorRunRequest(BaseModel):
    """POST /api/monitor/run — optional filter and caps."""

    source_ids: Optional[list[str]] = None
    limit: int = 50
    auto_extract: bool = True


class IngestRunItem(BaseModel):
    """Per-source row inside an ingestion run."""

    name: Optional[str] = None
    url: Optional[str] = None
    state: Optional[str] = None
    tax_type: Optional[str] = None
    source_id: Optional[str] = None
    source_type: Optional[str] = None
    status: str  # ingested | duplicate | failed | updated | unchanged | skipped | crawled
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


class AuditLogPublic(BaseModel):
    """Governed audit row (maps DB ``AuditLogEntry``; ``entity_*`` mirrors ``resource_*`` columns)."""

    id: str
    created_at: datetime
    actor: Optional[str] = None
    user_role: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    detail: Optional[dict[str, Any]] = None


class AuditLogsResponse(BaseModel):
    logs: list[AuditLogPublic]
    total: int


# ---------------------------------------------------------------------------
# Dashboard (Phase 9)
# ---------------------------------------------------------------------------


class DashboardActivityOut(BaseModel):
    id: str
    kind: str
    title: str
    detail: str
    context: str = ""
    confidence_pct: Optional[int] = None
    ref_type: Optional[str] = None
    ref_id: Optional[str] = None
    created_at: datetime


class DashboardAlertOut(BaseModel):
    id: str
    severity: str
    title: str
    body: str
    ref_type: Optional[str] = None
    ref_id: Optional[str] = None


class DashboardKPIsOut(BaseModel):
    total_sources: int
    total_rules: int
    published_rules: int
    rules_in_review: int
    avg_confidence: float
    failed_sources: int
    last_ingestion_run: Optional[dict[str, Any]] = None
    llm_enabled: bool
    retrieval_mode: str = "lexical"
    embedding_provider: str = "none"
    vector_index_size: int = 0


class DashboardOut(BaseModel):
    kpis: DashboardKPIsOut
    activities: list[DashboardActivityOut]
    alerts: list[DashboardAlertOut]


# ---------------------------------------------------------------------------
# Analytics (Phase 10)
# ---------------------------------------------------------------------------


class AnalyticsStateRow(BaseModel):
    state: str
    count: int


class AnalyticsCategoryRow(BaseModel):
    category: str
    count: int


class AnalyticsLabelCount(BaseModel):
    label: str
    count: int


class AnalyticsMethodRow(BaseModel):
    method: str
    count: int


class AnalyticsDayCount(BaseModel):
    date: str
    count: int


class AnalyticsFreshnessRow(BaseModel):
    bucket: str
    label: str
    count: int


class AnalyticsSummaryOut(BaseModel):
    total_rules: int
    total_sources: int
    published_rules: int
    rules_in_review: int
    rules_created_in_window: int
    source_content_changes_in_window: int
    review_events_in_window: int


class AnalyticsOut(BaseModel):
    rules_by_state: list[AnalyticsStateRow]
    rules_by_tax_category: list[AnalyticsCategoryRow]
    confidence_distribution: list[AnalyticsLabelCount]
    sources_by_status: dict[str, int]
    extraction_methods: list[AnalyticsMethodRow]
    rules_created_by_day: list[AnalyticsDayCount]
    review_events_by_day: list[AnalyticsDayCount]
    source_freshness: list[AnalyticsFreshnessRow]
    window_days: int
    summary: AnalyticsSummaryOut


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
    validation_payload: Optional[dict[str, Any]] = None


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


# ---------------------------------------------------------------------------
# Submission enforcement & outcomes (deterministic, no LLM)
# ---------------------------------------------------------------------------


class ValidateSubmissionRequest(BaseModel):
    state: str = Field(..., description="State name or USPS abbreviation (e.g. CA).")
    tax_category: str
    workflow_stage: Optional[str] = None
    effective_date: Optional[str] = Field(
        None, description="As-of date for effective range checks (YYYY-MM-DD)."
    )
    program_variant: Optional[dict[str, Any]] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    debug: bool = Field(
        False,
        description="When true, skip validation result caching.",
    )


class ViolationSourceOut(BaseModel):
    source_id: Optional[str] = None
    source_url: Optional[str] = None
    snippet: Optional[str] = None


class SubmissionViolationOut(BaseModel):
    rule_id: str
    rule_title: str
    reason: str
    required_action: str
    required_documentation: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    source: ViolationSourceOut
    conditions_met: list[str] = Field(default_factory=list)
    conditions_failed: list[str] = Field(default_factory=list)


class PassedRuleOut(BaseModel):
    rule_id: str
    rule_title: str


class ValidateSubmissionResponse(BaseModel):
    valid: bool
    risk_level: str = Field(..., description="high | medium | low")
    violations: list[SubmissionViolationOut]
    warnings: list[str] = Field(default_factory=list)
    passed_rules: list[PassedRuleOut] = Field(default_factory=list)
    explanation: str


class OutcomeCreateRequest(BaseModel):
    submission_id: Optional[str] = None
    state: str
    tax_category: str
    workflow_stage: Optional[str] = None
    effective_date: Optional[str] = None
    rejection_code: Optional[str] = None
    rejection_reason: str
    payload: Optional[dict[str, Any]] = None


class OutcomeValidationSnapshotOut(BaseModel):
    valid: bool
    risk_level: str
    violation_rule_ids: list[str] = Field(default_factory=list)


class OutcomeEventOut(BaseModel):
    id: str
    submission_id: Optional[str] = None
    state: str
    tax_category: str
    workflow_stage: Optional[str] = None
    rejection_code: Optional[str] = None
    rejection_reason: str
    normalized_root_cause: Optional[str] = None
    payload: Optional[dict[str, Any]] = None
    matched_rule_ids: list[str] = Field(default_factory=list)
    coverage_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class OutcomeCreateResponse(BaseModel):
    outcome: OutcomeEventOut
    coverage_status: str
    matched_rule_ids: list[str] = Field(default_factory=list)
    validation_at_outcome: OutcomeValidationSnapshotOut


class RejectionCoverageRow(BaseModel):
    coverage_status: str
    count: int


class RejectionReasonCount(BaseModel):
    reason: str
    count: int


class MissingRuleCluster(BaseModel):
    label: str
    count: int


class RejectionCoverageOut(BaseModel):
    total_outcomes: int
    by_coverage_status: list[RejectionCoverageRow]
    top_rejection_reasons: list[RejectionReasonCount]
    missing_rule_clusters: list[MissingRuleCluster]
    coverage_percentage: float = Field(
        ...,
        description="Share of outcomes tagged prevented_by_existing_rule (percent).",
    )


class RejectionPatternRow(BaseModel):
    state: str
    tax_category: str
    coverage_status: str
    count: int


class RejectionPatternsOut(BaseModel):
    by_state: list[RejectionPatternRow]
    by_tax_category: list[RejectionPatternRow]
    by_coverage: list[RejectionPatternRow]
    rule_coverage_report: dict[str, float] = Field(
        default_factory=dict,
        description="Approximate percentages for prevented / missed / unclear.",
    )


class SubmissionPathOut(BaseModel):
    recommended_path: str
    steps: list[str]
    required_documents: list[str]
    submission_methods: list[str]
    ranked_options: list[dict[str, Any]]
    portal_urls: list[str] = Field(default_factory=list)
    transaction_type: Optional[str] = None


class WorkflowStartBody(BaseModel):
    state: Optional[str] = None
    tax_category: Optional[str] = None
    title: Optional[str] = None
    org: Optional[str] = None
    template_id: Optional[str] = None
    case_id: Optional[str] = None
    actor: Optional[str] = None
    validation_payload: Optional[dict[str, Any]] = None


class WorkflowAdvanceBody(BaseModel):
    validation_payload: Optional[dict[str, Any]] = None
    actor: Optional[str] = None


class WorkflowAdvanceOut(BaseModel):
    blocked: bool
    case: Optional[dict[str, Any]] = None
    validation: Optional[dict[str, Any]] = None


class WebhookRegisterBody(BaseModel):
    url: str
    events: list[str] = Field(
        default_factory=lambda: [
            "rule.published",
            "submission.validated",
            "outcome.created",
        ]
    )
    tenant_id: str = "default"


class WebhookOut(BaseModel):
    id: str
    url: str
    events: list[str]
    active: bool
    secret_hint: Optional[str] = None


class WebhookRegisterResponse(WebhookOut):
    """Returned once from POST /register; signing_secret is only returned on creation."""

    signing_secret: Optional[str] = Field(
        None,
        description="HMAC signing key; store securely — not shown again.",
    )


class WebhookDeliveryPublic(BaseModel):
    id: str
    subscription_id: str
    event_type: str
    status: str
    attempt_count: int
    last_error: Optional[str] = None
    response_status_code: Optional[int] = None
    response_body_preview: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class WebhookDeliveriesResponse(BaseModel):
    deliveries: list[WebhookDeliveryPublic]


class WebhookFailurePublic(BaseModel):
    id: str
    url: str
    event_type: str
    last_error: Optional[str] = None
    created_at: datetime


class WebhookHealthOut(BaseModel):
    total_subscriptions: int
    active_subscriptions: int
    deliveries_last_24h: int
    success_last_24h: int
    failed_last_24h: int
    success_rate_last_24h: float
    recent_failures: list[WebhookFailurePublic]


class DemoResetOut(BaseModel):
    deleted_outcomes: int
    status: str


class CacheNamespaceStatsOut(BaseModel):
    hits: int
    misses: int
    sets: int
    invalidations: int
    current_size: int


class CacheMetricsOut(BaseModel):
    global_process_cache_stats: bool = True
    namespaces: dict[str, CacheNamespaceStatsOut]


class CacheClearRequest(BaseModel):
    namespace: Optional[str] = None


class KpiSummaryOut(BaseModel):
    rules_published: int
    outcome_events: int
    active_sources: int


class CanonicalConsistencyReportOut(BaseModel):
    total_rules: int
    rules_missing_jurisdiction_id: int
    rules_missing_program_variant_ref_id: int
    rules_with_legacy_program_variant_but_no_fk: int
    rules_with_rejection_map_but_no_links: int
    rules_by_review_status: dict[str, int]
    rules_by_tenant_id: dict[str, int]


class CanonicalBackfillRequest(BaseModel):
    target: Literal["all", "jurisdictions", "program_variants", "rejection_links"] = "all"
    dry_run: bool = True


class CanonicalBackfillResponse(BaseModel):
    dry_run: bool
    target: str
    changes: list[dict[str, Any]]
    summary: dict[str, int]


class PublishDiagnosticItemOut(BaseModel):
    code: str
    message: str
    severity: Literal["error", "warning"]


class PublishReadinessOut(BaseModel):
    rule_id: str
    can_publish: bool
    strict_mode_enabled: bool
    blockers: list[PublishDiagnosticItemOut]
    warnings: list[PublishDiagnosticItemOut]
    checked_fields: dict[str, bool]


class GovernanceConfigOut(BaseModel):
    strict_publish_checks: bool
    min_publish_confidence: float


SourceDetail.model_rebuild()
QueryResponse.model_rebuild()
