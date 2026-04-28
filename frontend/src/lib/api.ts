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

export interface Rule {
  id: string;
  state: string;
  tax_category: TaxType | string;
  rule_category?: string | null;
  rule_title: string;
  rule_summary: string;
  detailed_rule?: string | null;
  conditions?: string[] | null;
  required_actions?: string[] | null;
  required_forms?: string[] | null;
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
  rules_used: Rule[];
  question_id: string;
  answered_at: string;
}

export interface SourceRow {
  id: string;
  source_type: string;
  name: string;
  url?: string | null;
  file_path?: string | null;
  state?: string | null;
  tax_category?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  chunk_count: number;
  rule_count: number;
}

export interface IngestResult {
  source: SourceRow;
  chunks_created: number;
  rules_created: number;
  extraction_method: string;
}

export interface IngestRunResult {
  total: number;
  ingested: number;
  duplicates: number;
  errors: number;
  items: Array<{
    name: string;
    url?: string | null;
    state?: string | null;
    tax_type?: string | null;
    status: "ingested" | "duplicate" | "error";
    chunks_created: number;
    rules_created: number;
    extraction_method?: string | null;
    error?: string | null;
  }>;
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

  states: () => request<StateOut[]>("/api/states"),

  query: (payload: {
    question: string;
    state?: string;
    tax_type?: TaxType;
    top_k?: number;
  }) => request<QueryResponse>("/api/query", { method: "POST", json: payload }),

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
  }) =>
    request<IngestResult>("/api/ingest/source", {
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
    payload: { action: "approve" | "reject" | "publish" | "needs_review"; notes?: string }
  ) =>
    request<Rule>(`/api/review/rules/${id}/action`, {
      method: "POST",
      json: payload,
    }),
  ruleEvents: (id: string) =>
    request<ReviewEvent[]>(`/api/review/rules/${id}/events`),
};

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
