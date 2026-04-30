// Typed fetch client for the FastAPI backend.
// Vite proxies /api/* to http://localhost:8000 by default (see vite.config.ts).
// In production, set VITE_API_BASE to the absolute backend URL.


import { toast } from "sonner";

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ?? "";

export type TaxType =
  | "general_tax"
  | "sales_tax"
  | "payroll_tax"
  | "corporate_tax"
  | "income_tax"
  | "withholding"
  | "franchise_tax"
  | "other";

export type ReviewStatus =
  | "draft"
  | "auto_validated"
  | "needs_review"
  | "approved"
  | "published"
  | "rejected";

export interface StateOut {
  name: string;
  abbreviation: string;
}

export interface AdminRole {
  id: string;
  label: string;
  description: string;
}

export interface AdminTaxonomy {
  states: StateOut[];
  tax_categories: string[];
  workflow_stages: string[];
  source_types: string[];
  review_statuses: string[];
}

export interface AdminSummary {
  total_sources: number;
  total_rules: number;
  published_rules: number;
  rules_in_review: number;
  failed_sources: number;
  avg_confidence: number;
  extraction_breakdown: Record<string, number>;
  last_ingestion_run: {
    id: string;
    kind: string;
    status: string;
    started_at: string;
    finished_at: string | null;
    total: number;
    ingested: number;
    errors: number;
  } | null;
  llm_enabled: boolean;
  retrieval_mode: string;
  embedding_provider: string;
  vector_index_size: number;
}

export interface DashboardActivity {
  id: string;
  kind: string;
  title: string;
  detail: string;
  context: string;
  confidence_pct: number | null;
  ref_type: string | null;
  ref_id: string | null;
  created_at: string;
}

export interface DashboardAlert {
  id: string;
  severity: string;
  title: string;
  body: string;
  ref_type: string | null;
  ref_id: string | null;
}

export interface DashboardKPIs {
  total_sources: number;
  total_rules: number;
  published_rules: number;
  rules_in_review: number;
  avg_confidence: number;
  failed_sources: number;
  last_ingestion_run: AdminSummary["last_ingestion_run"];
  llm_enabled: boolean;
  retrieval_mode: string;
  embedding_provider: string;
  vector_index_size: number;
}

export interface DashboardResponse {
  kpis: DashboardKPIs;
  activities: DashboardActivity[];
  alerts: DashboardAlert[];
}

export interface AnalyticsSummary {
  total_rules: number;
  total_sources: number;
  published_rules: number;
  rules_in_review: number;
  rules_created_in_window: number;
  source_content_changes_in_window: number;
  review_events_in_window: number;
}

export interface AnalyticsResponse {
  rules_by_state: { state: string; count: number }[];
  rules_by_tax_category: { category: string; count: number }[];
  confidence_distribution: { label: string; count: number }[];
  sources_by_status: Record<string, number>;
  extraction_methods: { method: string; count: number }[];
  rules_created_by_day: { date: string; count: number }[];
  review_events_by_day: { date: string; count: number }[];
  source_freshness: { bucket: string; label: string; count: number }[];
  window_days: number;
  summary: AnalyticsSummary;
}

export interface ViolationSource {
  source_id?: string | null;
  source_url?: string | null;
  snippet?: string | null;
}

export interface SubmissionViolation {
  rule_id: string;
  rule_title: string;
  reason: string;
  required_action: string;
  required_documentation: string[];
  confidence: number;
  source: ViolationSource;
  conditions_met: string[];
  conditions_failed: string[];
}

export interface ValidateSubmissionResponse {
  valid: boolean;
  risk_level: string;
  violations: SubmissionViolation[];
  warnings: string[];
  passed_rules: { rule_id: string; rule_title: string }[];
  explanation: string;
}

export interface OutcomeEvent {
  id: string;
  submission_id?: string | null;
  state: string;
  tax_category: string;
  workflow_stage?: string | null;
  rejection_code?: string | null;
  rejection_reason: string;
  normalized_root_cause?: string | null;
  payload?: Record<string, unknown> | null;
  matched_rule_ids: string[];
  coverage_status: string;
  created_at: string;
}

export interface OutcomeCreateResponse {
  outcome: OutcomeEvent;
  coverage_status: string;
  matched_rule_ids: string[];
  validation_at_outcome: {
    valid: boolean;
    risk_level: string;
    violation_rule_ids: string[];
  };
}

export interface RejectionCoverageResponse {
  total_outcomes: number;
  by_coverage_status: { coverage_status: string; count: number }[];
  top_rejection_reasons: { reason: string; count: number }[];
  missing_rule_clusters: { label: string; count: number }[];
  coverage_percentage: number;
}

export interface ReviewAuditEvent {
  id: string;
  rule_id: string;
  rule_title: string;
  state: string;
  tax_category: string;
  action: string;
  actor: string | null;
  notes: string | null;
  diff: Record<string, unknown> | null;
  created_at: string;
}

/** Governed audit row (GET /api/audit). */
export interface AuditLogPublic {
  id: string;
  created_at: string;
  actor: string | null;
  user_role: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  detail: Record<string, unknown> | null;
}

export interface AuditLogsResponse {
  logs: AuditLogPublic[];
  total: number;
}

export type AppRoleId = "admin" | "reviewer" | "viewer";

const ROLE_STORAGE_KEY = "rules_intel_app_role";
export const TENANT_STORAGE_KEY = "rules_intel_tenant_id";
export const DEMO_USER_ID = "demo-user";

function normalizeLegacyStoredRole(raw: string | null): AppRoleId | null {
  if (raw === "readonly") return "viewer";
  if (raw === "admin" || raw === "reviewer" || raw === "viewer") return raw;
  return null;
}

/** Role string sent as `X-User-Role` (`readonly` maps to viewer). */
export function getApiRoleHeader(): AppRoleId {
  return (
    normalizeLegacyStoredRole(
      typeof localStorage !== "undefined"
        ? localStorage.getItem(ROLE_STORAGE_KEY)
        : null,
    ) ?? (import.meta.env.DEV ? "admin" : "viewer")
  );
}

export function getAppRole(): AppRoleId {
  try {
    const v = localStorage.getItem(ROLE_STORAGE_KEY);
    if (v === "readonly") {
      localStorage.setItem(ROLE_STORAGE_KEY, "viewer");
      return "viewer";
    }
    const n = normalizeLegacyStoredRole(v);
    if (n) return n;
  } catch {
    /* ignore */
  }
  return import.meta.env.DEV ? "admin" : "viewer";
}

export function setAppRole(role: AppRoleId): void {
  try {
    localStorage.setItem(ROLE_STORAGE_KEY, role);
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("rules_intel_app_role"));
    }
  } catch {
    /* ignore */
  }
}

export function getTenantId(): string {
  try {
    const v = typeof localStorage !== "undefined" ? localStorage.getItem(TENANT_STORAGE_KEY) : null;
    const t = (v ?? "").trim();
    if (t) return t;
  } catch {
    /* ignore */
  }
  return "default";
}

export function setTenantId(tenantId: string): void {
  const t = (tenantId ?? "").trim() || "default";
  try {
    localStorage.setItem(TENANT_STORAGE_KEY, t);
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("rules_intel_tenant_id"));
    }
  } catch {
    /* ignore */
  }
}

export function rbacHeaders(existing?: HeadersInit): HeadersInit {
  const h =
    existing instanceof Headers ? existing : new Headers(existing ?? undefined);
  h.set("X-User-Role", getApiRoleHeader());
  h.set("X-User-Id", DEMO_USER_ID);
  h.set("X-Tenant-Id", getTenantId());
  return h;
}

export interface Rule {
  id: string;
  state: string;
  tax_category: TaxType | string;
  rule_category?: string | null;
  workflow_stage?: string | null;
  operating_scenario?: string | null;
  condition_logic?: string | null;
  submission_method?: string | null;
  program_variant?: Record<string, unknown> | null;
  rule_title: string;
  rule_summary: string;
  detailed_rule?: string | null;
  conditions?: string[] | null;
  required_actions?: string[] | null;
  required_forms?: string[] | null;
  required_documentation?: string[] | null;
  deadlines?: string[] | null;
  exceptions?: string[] | null;
  source_id?: string | null;
  source_url?: string | null;
  source_document_name?: string | null;
  source_snippet?: string | null;
  effective_date?: string | null;
  effective_date_end?: string | null;
  confidence_score: number;
  review_status: ReviewStatus;
  extraction_method?: string | null;
  lineage?: Record<string, unknown> | null;
  validation_errors?: string[] | null;
  validation_warnings?: string[] | null;
  current_version?: number;
  supersedes_rule_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface QuerySource {
  title: string;
  url?: string | null;
  snippet: string;
  document_type: string;
  last_checked?: string | null;
  state?: string | null;
  tax_type?: string | null;
  relevance: number;
}

export interface QueryResponse {
  answer: string;
  state?: string | null;
  tax_type?: string | null;
  sources: QuerySource[];
  confidence: number;
  method: "llm" | "fallback";
  retrieval_mode?: "lexical" | "hybrid" | string;
  rules_used: Rule[];
  chunks_used?: string[];
  source_versions_used?: string[];
  safety_flags?: string[];
  question_id: string;
  answered_at: string;
}

export type SourceStatus =
  | "pending"
  | "processing"
  | "processed"
  | "failed"
  | "skipped_duplicate";

export interface SourceRow {
  id: string;
  source_type: string;
  name: string;
  url?: string | null;
  canonical_url?: string | null;
  file_path?: string | null;
  state?: string | null;
  tax_category?: string | null;
  status: SourceStatus | string;
  error_message?: string | null;
  checksum?: string | null;
  last_checked?: string | null;
  last_changed?: string | null;
  current_version?: number;
  created_at: string;
  updated_at: string;
  chunk_count: number;
  rule_count: number;
}

export interface RuleVersion {
  id: string;
  rule_id: string;
  version: number;
  previous_data?: Record<string, unknown> | null;
  new_data?: Record<string, unknown> | null;
  changed_fields?: string[] | null;
  extraction_method?: string | null;
  source_version_id?: string | null;
  actor?: string | null;
  notes?: string | null;
  captured_reason?: string | null;
  created_at: string;
}

export interface RuleValidation {
  valid: boolean;
  errors: string[];
  warnings: string[];
  suggested_review_status: ReviewStatus | string;
  adjusted_confidence: number;
}

export interface RuleConflicts {
  duplicate_of?: string | null;
  conflicting_rule_ids: string[];
  notes: string[];
}

export interface RuleAssessment {
  rule_id: string;
  validation: RuleValidation;
  conflicts: RuleConflicts;
}

export interface SourceVersion {
  id: string;
  source_id: string;
  version: number;
  checksum?: string | null;
  canonical_url?: string | null;
  title?: string | null;
  raw_text_preview?: string | null;
  status_at_capture?: string | null;
  captured_reason?: string | null;
  created_at: string;
}

export interface SourceChunk {
  id: string;
  chunk_index: number;
  text: string;
  page_number?: number | null;
  url_section?: string | null;
}

export interface SourceDetail extends SourceRow {
  raw_text_preview?: string | null;
  meta?: Record<string, unknown> | null;
  chunks: SourceChunk[];
  rules: Rule[];
}

export interface LinkHealth {
  url: string;
  ok: boolean;
  status_code?: number | null;
  canonical_url?: string | null;
  content_type?: string | null;
  error?: string | null;
  checked_at: string;
}

export interface IngestResult {
  source: SourceRow;
  chunks_created: number;
  rules_created: number;
  extraction_method: string;
}

export type IngestRunItemStatus =
  | "ingested"
  | "duplicate"
  | "failed"
  | "updated"
  | "unchanged"
  | "skipped"
  | "crawled"
  | "error";

export interface IngestRunItem {
  name?: string | null;
  url?: string | null;
  state?: string | null;
  tax_type?: string | null;
  source_id?: string | null;
  source_type?: string | null;
  status: IngestRunItemStatus;
  chunks_created: number;
  rules_created: number;
  extraction_method?: string | null;
  error?: string | null;
  error_message?: string | null;
  created_at?: string | null;
}

export interface IngestRunResult {
  total: number;
  ingested: number;
  duplicates: number;
  errors: number;
  items: IngestRunItem[];
  run_id?: string | null;
}

export interface IngestionRunSummary {
  id: string;
  kind: string;
  status: string;
  triggered_by?: string | null;
  only_state?: string | null;
  only_tax_type?: string | null;
  notes?: string | null;
  total: number;
  ingested: number;
  duplicates: number;
  errors: number;
  started_at: string;
  finished_at?: string | null;
}

export interface IngestionRunDetail extends IngestionRunSummary {
  items: IngestRunItem[];
}

export interface ReviewEvent {
  id: string;
  rule_id: string;
  action: string;
  actor?: string | null;
  notes?: string | null;
  diff?: Record<string, unknown> | null;
  created_at: string;
}

export interface Health {
  status: string;
  llm_enabled: boolean;
  database: string;
  demo_mode?: boolean;
  embedding_provider?: string;
  embedding_enabled?: boolean;
  vector_backend?: string;
  vector_enabled?: boolean;
  vector_index_size?: number;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public detail?: unknown,
  ) {
    super(message);
  }
}

async function request<T>(
  path: string,
  init?: RequestInit & { json?: unknown }
): Promise<T> {
  const merged = rbacHeaders(init?.headers as HeadersInit | undefined);
  const headers =
    merged instanceof Headers ? merged : new Headers(merged);
  let body: BodyInit | undefined = init?.body as BodyInit | undefined;
  if (init?.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(init.json);
  }
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers, body });
  if (!res.ok) {
    if (res.status === 403) {
      toast.error(
        "You need reviewer or admin access for this action.",
      );
    }
    let detail = res.statusText;
    let detailObj: unknown = undefined;
    try {
      const data = await res.json();
      detail = data.detail ?? JSON.stringify(data);
      detailObj = data.detail ?? data;
    } catch {
      // ignore
    }
    throw new ApiError(res.status, `${res.status} ${detail}`, detailObj);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** GET `/api/audit` (reviewer or admin RBAC headers). */
export function getAuditLogs(params?: {
  entity_type?: string;
  entity_id?: string;
  action?: string;
  actor?: string;
  limit?: number;
  offset?: number;
}): Promise<AuditLogsResponse> {
  const q = new URLSearchParams();
  if (params?.entity_type) q.set("entity_type", params.entity_type);
  if (params?.entity_id) q.set("entity_id", params.entity_id);
  if (params?.action) q.set("action", params.action);
  if (params?.actor) q.set("actor", params.actor);
  if (params?.limit != null) q.set("limit", String(params.limit));
  if (params?.offset != null) q.set("offset", String(params.offset));
  const qs = q.toString();
  return request<AuditLogsResponse>(`/api/audit${qs ? `?${qs}` : ""}`);
}

export const api = {
  health: () => request<Health>("/health"),

  adminRoles: () => request<AdminRole[]>("/api/admin/roles"),
  adminTaxonomy: () => request<AdminTaxonomy>("/api/admin/taxonomy"),
  adminSummary: () => request<AdminSummary>("/api/admin/summary"),
  adminAudit: (limit?: number) =>
    request<ReviewAuditEvent[]>(
      `/api/admin/audit${limit != null ? `?limit=${limit}` : ""}`,
    ),

  getAuditLogs,

  dashboard: (activityLimit?: number) =>
    request<DashboardResponse>(
      `/api/dashboard${activityLimit != null ? `?activity_limit=${activityLimit}` : ""}`,
    ),

  analytics: (days?: number) =>
    request<AnalyticsResponse>(
      `/api/analytics${days != null ? `?days=${days}` : ""}`,
    ),

  rejectionCoverage: () =>
    request<RejectionCoverageResponse>("/api/analytics/rejection-coverage"),

  rejectionPatterns: () =>
    request<RejectionPatternsResponse>("/api/analytics/rejection-patterns"),

  submissionPath: (params: {
    state: string;
    tax_category: string;
    workflow_stage?: string;
    transaction_type?: string;
  }) => {
    const q = new URLSearchParams();
    q.set("state", params.state);
    q.set("tax_category", params.tax_category);
    if (params.workflow_stage) q.set("workflow_stage", params.workflow_stage);
    if (params.transaction_type) q.set("transaction_type", params.transaction_type);
    return request<SubmissionPathResponse>(`/api/submission-path?${q}`);
  },

  workflowStart: (payload: {
    state?: string;
    tax_category?: string;
    title?: string;
    validation_payload?: Record<string, unknown>;
  }) =>
    request<CaseWorkflow>(
      "/api/workflows/start",
      { method: "POST", json: payload },
    ),

  workflowAdvance: (
    caseId: string,
    payload?: { validation_payload?: Record<string, unknown>; actor?: string },
  ) =>
    request<WorkflowAdvanceResponse>(
      `/api/workflows/${encodeURIComponent(caseId)}/advance`,
      { method: "POST", json: payload ?? {} },
    ),

  platformKpis: () => request<KpiSummary>("/api/platform/kpis"),
  platformCache: () => request<CacheMetricsOut>("/api/platform/cache"),
  platformCacheClear: (body?: { namespace?: string }) =>
    request<{ status: string }>("/api/platform/cache/clear", {
      method: "POST",
      json: body ?? {},
    }),

  canonicalReport: () => request<CanonicalConsistencyReportOut>("/api/platform/canonical-report"),
  canonicalBackfill: (payload: {
    target: "all" | "jurisdictions" | "program_variants" | "rejection_links";
    dry_run: boolean;
  }) =>
    request<CanonicalBackfillResponseOut>("/api/platform/backfill", {
      method: "POST",
      json: payload,
    }),

  platformGovernanceConfig: () =>
    request<GovernanceConfigOut>("/api/platform/governance-config"),

  webhookSubscriptions: (activeOnly = false) =>
    request<WebhookSubscriptionRow[]>(
      `/api/webhooks/subscriptions?active_only=${activeOnly}`,
    ),

  webhookHealth: () => request<WebhookHealthOut>("/api/webhooks/health"),

  webhookDeliveries: (params?: {
    status?: string;
    event_type?: string;
    limit?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.event_type) q.set("event_type", params.event_type);
    if (params?.limit != null) q.set("limit", String(params.limit));
    const qs = q.toString();
    return request<WebhookDeliveriesList>(
      `/api/webhooks/deliveries${qs ? `?${qs}` : ""}`,
    );
  },

  webhookResendDelivery: (deliveryId: string) =>
    request<WebhookDeliveryRow>(
      `/api/webhooks/deliveries/${encodeURIComponent(deliveryId)}/resend`,
      { method: "POST" },
    ),

  demoReset: () =>
    request<{ deleted_outcomes: number; status: string }>("/api/demo/reset", {
      method: "POST",
    }),

  validateSubmission: (payload: {
    state: string;
    tax_category: string;
    workflow_stage?: string;
    effective_date?: string;
    program_variant?: Record<string, unknown>;
    payload: Record<string, unknown>;
  }) =>
    request<ValidateSubmissionResponse>("/api/validate-submission", {
      method: "POST",
      json: payload,
    }),

  createOutcome: (payload: {
    submission_id?: string;
    state: string;
    tax_category: string;
    workflow_stage?: string;
    effective_date?: string;
    rejection_code?: string;
    rejection_reason: string;
    payload?: Record<string, unknown>;
  }) =>
    request<OutcomeCreateResponse>("/api/outcomes", { method: "POST", json: payload }),

  listOutcomes: (params?: {
    state?: string;
    tax_category?: string;
    coverage_status?: string;
    limit?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.state) q.set("state", params.state);
    if (params?.tax_category) q.set("tax_category", params.tax_category);
    if (params?.coverage_status) q.set("coverage_status", params.coverage_status);
    if (params?.limit != null) q.set("limit", String(params.limit));
    const qs = q.toString();
    return request<OutcomeEvent[]>(`/api/outcomes${qs ? `?${qs}` : ""}`);
  },

  monitorRun: (payload?: { source_ids?: string[]; limit?: number; auto_extract?: boolean }) =>
    request<IngestRunResult>("/api/monitor/run", {
      method: "POST",
      json: payload ?? {},
    }),

  states: () => request<StateOut[]>("/api/states"),

  query: (payload: {
    question: string;
    state?: string;
    tax_type?: TaxType;
    workflow_stage?: string;
    operating_scenario?: string;
    statuses?: string[];
    top_k?: number;
  }) => request<QueryResponse>("/api/query", { method: "POST", json: payload }),

  reindexVectors: () =>
    request<{ reindexed_chunks: number } & Record<string, unknown>>(
      "/api/sources/reindex",
      { method: "POST" },
    ),

  // Rules
  rules: (params?: {
    state?: string;
    tax_type?: TaxType;
    review_status?: ReviewStatus;
    workflow_stage?: string;
  }) => {
    const q = new URLSearchParams();
    if (params?.state) q.set("state", params.state);
    if (params?.tax_type) q.set("tax_type", params.tax_type);
    if (params?.review_status) q.set("review_status", params.review_status);
    if (params?.workflow_stage) q.set("workflow_stage", params.workflow_stage);
    const qs = q.toString();
    return request<Rule[]>(`/api/rules${qs ? `?${qs}` : ""}`);
  },

  // Sources & ingestion
  listSources: () => request<SourceRow[]>("/api/sources"),
  deleteSource: (id: string) =>
    request<{ deleted: string }>(`/api/sources/${id}`, { method: "DELETE" }),

  ingestSource: (payload: {
    source_type?: string;
    url?: string;
    title?: string;
    text?: string;
    state?: string;
    tax_type?: TaxType;
    auto_extract?: boolean;
    crawl_depth?: number;
    crawl_max_pages?: number;
  }) =>
    request<IngestRunResult>("/api/ingest/source", {
      method: "POST",
      json: payload,
    }),

  ingestRun: (payload?: {
    only_state?: string;
    only_tax_type?: TaxType;
    auto_extract?: boolean;
  }) =>
    request<IngestRunResult>("/api/ingest/run", {
      method: "POST",
      json: payload ?? {},
    }),

  ingestRuns: (limit?: number) =>
    request<IngestionRunSummary[]>(
      `/api/ingest/runs${limit ? `?limit=${limit}` : ""}`,
    ),

  ingestRunDetail: (id: string) =>
    request<IngestionRunDetail>(`/api/ingest/runs/${id}`),

  sourceDetail: (id: string) =>
    request<SourceDetail>(`/api/sources/${id}`),

  checkSource: (id: string) =>
    request<LinkHealth>(`/api/sources/${id}/check`, { method: "POST" }),

  ruleVersions: (id: string) =>
    request<RuleVersion[]>(`/api/rules/${id}/versions`),

  sourceVersions: (id: string) =>
    request<SourceVersion[]>(`/api/sources/${id}/versions`),

  validateRule: (id: string) =>
    request<RuleAssessment>(`/api/rules/${id}/validate`, { method: "POST" }),

  publishReadiness: (id: string) =>
    request<PublishReadinessOut>(`/api/rules/${id}/publish-readiness`),

  ruleConflicts: (id: string) =>
    request<Rule[]>(`/api/rules/${id}/conflicts`),

  uploadFile: async (
    file: File,
    options?: { state?: string; tax_type?: TaxType; auto_extract?: boolean }
  ) => {
    const fd = new FormData();
    fd.append("file", file);
    if (options?.state) fd.append("state", options.state);
    if (options?.tax_type) fd.append("tax_category", options.tax_type);
    if (options?.auto_extract !== undefined)
      fd.append("auto_extract", String(options.auto_extract));
    return request<IngestResult>("/api/sources/upload", {
      method: "POST",
      body: fd,
    });
  },

  // Review
  reviewQueue: () => request<Rule[]>("/api/review/queue"),
  reviewAction: (
    id: string,
    payload: {
      action: "approve" | "reject" | "publish" | "needs_review";
      notes?: string;
      actor?: string;
    },
  ) =>
    request<Rule>(`/api/review/rules/${id}/action`, {
      method: "POST",
      json: payload,
    }),
  ruleEvents: (id: string) =>
    request<ReviewEvent[]>(`/api/review/rules/${id}/events`),

  // Workflows (Phase 7)
  workflowTemplates: (params?: { state?: string; tax_category?: TaxType | string }) => {
    const q = new URLSearchParams();
    if (params?.state) q.set("state", params.state);
    if (params?.tax_category) q.set("tax_category", params.tax_category as string);
    const qs = q.toString();
    return request<WorkflowTemplate[]>(
      `/api/workflows/templates${qs ? `?${qs}` : ""}`,
    );
  },
  workflowTemplate: (
    id: string,
    params?: { state?: string; tax_category?: TaxType | string },
  ) => {
    const q = new URLSearchParams();
    if (params?.state) q.set("state", params.state);
    if (params?.tax_category) q.set("tax_category", params.tax_category as string);
    const qs = q.toString();
    return request<WorkflowTemplate>(
      `/api/workflows/templates/${id}${qs ? `?${qs}` : ""}`,
    );
  },
  createCase: (payload: {
    state?: string;
    tax_category?: TaxType | string;
    title?: string;
    org?: string;
    template_id?: string;
    case_id?: string;
    actor?: string;
  }) =>
    request<CaseWorkflow>("/api/workflows/cases", {
      method: "POST",
      json: payload,
    }),
  listCases: (params?: {
    state?: string;
    tax_category?: TaxType | string;
    status?: string;
    limit?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.state) q.set("state", params.state);
    if (params?.tax_category) q.set("tax_category", params.tax_category as string);
    if (params?.status) q.set("status", params.status);
    if (params?.limit) q.set("limit", String(params.limit));
    const qs = q.toString();
    return request<CaseWorkflow[]>(`/api/workflows/cases${qs ? `?${qs}` : ""}`);
  },
  getCase: (id: string) => request<CaseWorkflow>(`/api/workflows/cases/${id}`),
  updateCaseStep: (
    id: string,
    payload: { step_key: string; completed?: boolean; notes?: string; actor?: string },
  ) =>
    request<CaseWorkflow>(`/api/workflows/cases/${id}/steps`, {
      method: "PATCH",
      json: payload,
    }),
};

export interface WorkflowChecklistItem {
  key: string;
  label: string;
  checked?: boolean | null;
}

export interface WorkflowRuleSummary {
  id: string;
  rule_title: string;
  rule_summary?: string | null;
  tax_category?: string | null;
  state?: string | null;
  workflow_stage?: string | null;
  required_forms?: string[];
  required_documentation?: string[];
  deadlines?: string[];
  exceptions?: string[];
  submission_method?: string | null;
  source_url?: string | null;
  confidence_score?: number | null;
  review_status?: string | null;
}

export interface WorkflowStep {
  key: string;
  title: string;
  description?: string | null;
  workflow_stage?: string | null;
  checklist: WorkflowChecklistItem[];
  rules: WorkflowRuleSummary[];
  rule_count?: number | null;
  aggregated_forms?: string[];
  aggregated_documents?: string[];
  aggregated_deadlines?: string[];
  aggregated_validations?: string[];
  status?: "pending" | "complete" | "active" | string | null;
  completed_at?: string | null;
  notes?: string | null;
}

export interface WorkflowTemplate {
  id: string;
  key: string;
  title: string;
  description?: string | null;
  state?: string | null;
  tax_category?: string | null;
  workflow_stage?: string | null;
  is_builtin: boolean;
  steps: WorkflowStep[];
  required_rule_filters?: Record<string, unknown>[];
  created_at: string;
  updated_at: string;
}

export interface CaseWorkflowEvent {
  id: string;
  action: string;
  step_key?: string | null;
  actor?: string | null;
  notes?: string | null;
  payload?: Record<string, unknown> | null;
  created_at: string;
}

export interface CaseWorkflow {
  id: string;
  case_id: string;
  title?: string | null;
  org?: string | null;
  template_id?: string | null;
  state?: string | null;
  tax_category?: string | null;
  current_stage?: string | null;
  status: "active" | "completed" | "abandoned" | string;
  steps: WorkflowStep[];
  completed_steps: string[];
  step_count: number;
  completed_count: number;
  progress: number;
  events?: CaseWorkflowEvent[];
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
  validation_payload?: Record<string, unknown> | null;
}

export interface SubmissionPathResponse {
  recommended_path: string;
  steps: string[];
  required_documents: string[];
  submission_methods: string[];
  ranked_options: Record<string, unknown>[];
  portal_urls?: string[];
  transaction_type?: string | null;
}

export interface WorkflowAdvanceResponse {
  blocked: boolean;
  case?: Record<string, unknown> | CaseWorkflow | null;
  validation?: Record<string, unknown> | null;
}

export interface RejectionPatternRow {
  state: string;
  tax_category: string;
  coverage_status: string;
  count: number;
}

export interface RejectionPatternsResponse {
  by_state: RejectionPatternRow[];
  by_tax_category: RejectionPatternRow[];
  by_coverage: RejectionPatternRow[];
  rule_coverage_report: Record<string, number>;
}

export interface KpiSummary {
  rules_published: number;
  outcome_events: number;
  active_sources: number;
}

export interface CacheNamespaceStats {
  hits: number;
  misses: number;
  sets: number;
  invalidations: number;
  current_size: number;
}

export interface CacheMetricsOut {
  namespaces: Record<string, CacheNamespaceStats>;
}

export interface CanonicalConsistencyReportOut {
  total_rules: number;
  rules_missing_jurisdiction_id: number;
  rules_missing_program_variant_ref_id: number;
  rules_with_legacy_program_variant_but_no_fk: number;
  rules_with_rejection_map_but_no_links: number;
  rules_by_review_status: Record<string, number>;
  rules_by_tenant_id: Record<string, number>;
}

export interface CanonicalBackfillResponseOut {
  dry_run: boolean;
  target: string;
  changes: Record<string, unknown>[];
  summary: Record<string, number>;
}

export interface PublishDiagnosticItemOut {
  code: string;
  message: string;
  severity: "error" | "warning";
}

export interface PublishReadinessOut {
  rule_id: string;
  can_publish: boolean;
  strict_mode_enabled: boolean;
  blockers: PublishDiagnosticItemOut[];
  warnings: PublishDiagnosticItemOut[];
  checked_fields: Record<string, boolean>;
}

export interface GovernanceConfigOut {
  strict_publish_checks: boolean;
  min_publish_confidence: number;
}

export interface WebhookSubscriptionRow {
  id: string;
  url: string;
  events: string[];
  active: boolean;
  secret_hint?: string | null;
}

export interface WebhookDeliveryRow {
  id: string;
  subscription_id: string;
  event_type: string;
  status: string;
  attempt_count: number;
  last_error?: string | null;
  response_status_code?: number | null;
  response_body_preview?: string | null;
  duration_ms?: number | null;
  created_at: string;
  updated_at?: string | null;
}

export interface WebhookDeliveriesList {
  deliveries: WebhookDeliveryRow[];
}

export interface WebhookFailurePublic {
  id: string;
  url: string;
  event_type: string;
  last_error?: string | null;
  created_at: string;
}

export interface WebhookHealthOut {
  total_subscriptions: number;
  active_subscriptions: number;
  deliveries_last_24h: number;
  success_last_24h: number;
  failed_last_24h: number;
  success_rate_last_24h: number;
  recent_failures: WebhookFailurePublic[];
}

export const TAX_TYPES: { value: TaxType; label: string }[] = [
  {
    value: "general_tax",
    label: "General / state portal",
  },
  { value: "sales_tax", label: "Sales tax" },
  { value: "payroll_tax", label: "Payroll tax" },
  { value: "corporate_tax", label: "Corporate tax" },
  { value: "income_tax", label: "Income tax" },
  { value: "withholding", label: "Withholding" },
  { value: "franchise_tax", label: "Franchise tax" },
  { value: "other", label: "Other" },
];

export function taxTypeLabel(t?: string | null): string {
  if (!t) return "—";
  const m = TAX_TYPES.find((x) => x.value === t);
  return m?.label ?? t.replace(/_/g, " ");
}

export function confidenceToPct(c: number | null | undefined): number {
  if (c == null) return 0;
  return Math.round(c * 100);
}
