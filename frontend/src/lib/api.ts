// Typed fetch client for the FastAPI backend.
// Vite proxies /api/* to http://localhost:8000 by default (see vite.config.ts).
// In production, set VITE_API_BASE to the absolute backend URL.

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ?? "";

export type TaxType =
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

export type AppRoleId = "admin" | "reviewer" | "readonly";

const ROLE_STORAGE_KEY = "rules_intel_app_role";

export function getAppRole(): AppRoleId {
  try {
    const v = localStorage.getItem(ROLE_STORAGE_KEY);
    if (v === "admin" || v === "reviewer" || v === "readonly") return v;
  } catch {
    /* ignore */
  }
  return "admin";
}

export function setAppRole(role: AppRoleId): void {
  try {
    localStorage.setItem(ROLE_STORAGE_KEY, role);
  } catch {
    /* ignore */
  }
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
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(
  path: string,
  init?: RequestInit & { json?: unknown }
): Promise<T> {
  const headers = new Headers(init?.headers);
  let body: BodyInit | undefined = init?.body as BodyInit | undefined;
  if (init?.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(init.json);
  }
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers, body });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || JSON.stringify(data);
    } catch {
      // ignore
    }
    throw new ApiError(res.status, `${res.status} ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
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
  }) => {
    const q = new URLSearchParams();
    if (params?.state) q.set("state", params.state);
    if (params?.tax_type) q.set("tax_type", params.tax_type);
    if (params?.review_status) q.set("review_status", params.review_status);
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
}

export const TAX_TYPES: { value: TaxType; label: string }[] = [
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
