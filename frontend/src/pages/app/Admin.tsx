import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  Database,
  FileUp,
  Gauge,
  Gavel,
  Layers,
  Link2,
  Loader2,
  Play,
  RefreshCw,
  Shield,
  Tag,
  AlertCircle,
  ScrollText,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  api,
  AdminSummary,
  AdminTaxonomy,
  AppRoleId,
  CacheMetricsOut,
  CanonicalBackfillResponseOut,
  CanonicalConsistencyReportOut,
  GovernanceConfigOut,
  getAppRole,
  getTenantId,
  setAppRole,
  setTenantId,
  ReviewAuditEvent,
  ReviewStatus,
  Rule,
  StateOut,
  TAX_TYPES,
  TaxType,
  taxTypeLabel,
} from "@/lib/api";

function timeAgo(iso: string): string {
  const t = new Date(iso).getTime();
  const diff = Date.now() - t;
  if (diff < 60_000) return "just now";
  if (diff < 3_600_000) return `${Math.round(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.round(diff / 3_600_000)}h ago`;
  return `${Math.round(diff / 86_400_000)}d ago`;
}

function auditSummaryLine(ev: ReviewAuditEvent): string {
  if (ev.action === "edit") return "Edited rule fields";
  if (ev.action === "approve") return "Approved rule";
  if (ev.action === "reject") return "Rejected rule";
  if (ev.action === "publish") return "Published rule";
  if (ev.action === "needs_review") return "Sent to review";
  return ev.action;
}

const Admin = () => {
  const [role, setRole] = useState<AppRoleId>(() => getAppRole());
  const [summary, setSummary] = useState<AdminSummary | null>(null);
  const [taxonomy, setTaxonomy] = useState<AdminTaxonomy | null>(null);
  const [audit, setAudit] = useState<ReviewAuditEvent[]>([]);
  const [rules, setRules] = useState<Rule[]>([]);
  const [rulesFilter, setRulesFilter] = useState<string>("");
  const [states, setStates] = useState<StateOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [cacheMetrics, setCacheMetrics] = useState<CacheMetricsOut | null>(null);
  const [canonicalReport, setCanonicalReport] = useState<CanonicalConsistencyReportOut | null>(null);
  const [lastCanonicalBackfill, setLastCanonicalBackfill] = useState<CanonicalBackfillResponseOut | null>(null);
  const [governanceConfig, setGovernanceConfig] = useState<GovernanceConfigOut | null>(null);

  const fileRef = useRef<HTMLInputElement>(null);
  const [url, setUrl] = useState("");
  const [urlTitle, setUrlTitle] = useState("");
  const [urlState, setUrlState] = useState("");
  const [urlTax, setUrlTax] = useState<TaxType | "">("");
  const [crawlDepth, setCrawlDepth] = useState("0");
  const [crawlMax, setCrawlMax] = useState("5");

  const isViewer = role === "viewer";
  const canPublish = role === "admin";

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [sum, tax, aud, st] = await Promise.all([
        api.adminSummary(),
        api.adminTaxonomy(),
        api.adminAudit(100),
        api.states(),
      ]);
      setSummary(sum);
      setTaxonomy(tax);
      setAudit(aud);
      setStates(st);
      const data = await api.rules(
        rulesFilter ? { review_status: rulesFilter as ReviewStatus } : undefined,
      );
      setRules(data.slice(0, 40));
      if (role !== "viewer") {
        try {
          setCacheMetrics(await api.platformCache());
        } catch {
          setCacheMetrics(null);
        }
        try {
          setCanonicalReport(await api.canonicalReport());
        } catch {
          setCanonicalReport(null);
        }
        try {
          setGovernanceConfig(await api.platformGovernanceConfig());
        } catch {
          setGovernanceConfig(null);
        }
      } else {
        setCacheMetrics(null);
        setCanonicalReport(null);
        setGovernanceConfig(null);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [rulesFilter, role]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const sync = () => setRole(getAppRole());
    window.addEventListener("rules_intel_app_role", sync);
    return () => window.removeEventListener("rules_intel_app_role", sync);
  }, []);

  const [tenant, setTenant] = useState<string>(() => getTenantId());

  useEffect(() => {
    const sync = () => setTenant(getTenantId());
    window.addEventListener("rules_intel_tenant_id", sync);
    return () => window.removeEventListener("rules_intel_tenant_id", sync);
  }, []);

  useEffect(() => {
    void load();
  }, [tenant, load]);

  const onRoleChange = (v: AppRoleId) => {
    setRole(v);
    setAppRole(v);
  };

  const onTenantChange = (v: string) => {
    const t = (v ?? "").trim() || "default";
    setTenant(t);
    setTenantId(t);
  };

  async function onIngestUrl(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim() || isViewer) return;
    setBusy("url");
    setError(null);
    try {
      await api.ingestSource({
        source_type: "webpage",
        url: url.trim(),
        title: urlTitle.trim() || undefined,
        state: urlState || undefined,
        tax_type: urlTax || undefined,
        auto_extract: true,
        crawl_depth: parseInt(crawlDepth, 10) || 0,
        crawl_max_pages: parseInt(crawlMax, 10) || 5,
      });
      setUrl("");
      setUrlTitle("");
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function onUpload(f: File | null) {
    if (!f || isViewer) return;
    setBusy("upload");
    setError(null);
    try {
      await api.uploadFile(f, {
        state: urlState || undefined,
        tax_type: urlTax || undefined,
        auto_extract: true,
      });
      if (fileRef.current) fileRef.current.value = "";
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function onYamlRun() {
    if (isViewer) return;
    setBusy("yaml");
    setError(null);
    try {
      await api.ingestRun({});
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function reviewAct(id: string, action: "approve" | "reject" | "publish" | "needs_review") {
    if (isViewer) return;
    if (action === "publish" && !canPublish) return;
    setBusy(`act-${id}`);
    setError(null);
    try {
      await api.reviewAction(id, { action, actor: role });
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function onClearCache() {
    if (!canPublish || isViewer) return;
    setBusy("cache-clear");
    setError(null);
    try {
      await api.platformCacheClear({});
      setCacheMetrics(await api.platformCache());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function runCanonicalBackfill(dry_run: boolean) {
    if (isViewer || (!dry_run && !canPublish)) return;
    setBusy(dry_run ? "canonical-dry" : "canonical-apply");
    setError(null);
    try {
      const res = await api.canonicalBackfill({ target: "all", dry_run });
      setLastCanonicalBackfill(res);
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  function exportAuditCsv() {
    const headers = ["created_at", "action", "actor", "rule_id", "rule_title", "state", "tax_category", "notes"];
    const rows = audit.map((a) =>
      headers.map((h) => {
        const v = (a as unknown as Record<string, string | null>)[h] ?? "";
        const s = String(v).replace(/"/g, '""');
        return `"${s}"`;
      }).join(","),
    );
    const blob = new Blob([[headers.join(","), ...rows].join("\n")], { type: "text/csv" });
    const u = URL.createObjectURL(blob);
    const el = document.createElement("a");
    el.href = u;
    el.download = "review-audit.csv";
    el.click();
    URL.revokeObjectURL(u);
  }

  const cats = taxonomy?.tax_categories ?? [];
  const stages = taxonomy?.workflow_stages ?? [];
  const srcTypes = taxonomy?.source_types ?? [];
  const taxStates = taxonomy?.states ?? states;

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-[1400px]">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="app-label">Workspace settings</p>
          <h1 className="font-serif text-3xl leading-tight tracking-tight mt-1">Admin</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Source onboarding, taxonomy reference, publishing controls, and review audit from the live backend.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`} />
            Reload
          </Button>
          <div className="flex flex-col gap-1">
            <Label className="text-[10px] uppercase text-muted-foreground">Session role (RBAC placeholder)</Label>
            <Select value={role} onValueChange={(v) => onRoleChange(v as AppRoleId)}>
              <SelectTrigger className="w-[180px] h-9">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="admin">Admin</SelectItem>
                <SelectItem value="reviewer">Reviewer</SelectItem>
                <SelectItem value="viewer">Viewer</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1">
            <Label className="text-[10px] uppercase text-muted-foreground">Tenant (demo isolation)</Label>
            <Select value={tenant} onValueChange={onTenantChange}>
              <SelectTrigger className="w-[200px] h-9">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="default">default</SelectItem>
                <SelectItem value="demo-client-a">demo-client-a</SelectItem>
                <SelectItem value="demo-client-b">demo-client-b</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-border/80 bg-secondary/25 px-4 py-3 text-xs text-muted-foreground max-w-3xl">
        <span className="font-medium text-foreground">Metrics shown for active tenant:</span>{" "}
        <code className="text-[10px] bg-secondary px-1 rounded">{tenant}</code>.{" "}
        <span className="font-medium text-foreground">Tenant isolation is header-based demo isolation.</span>{" "}
        API calls send <code className="text-[10px] bg-secondary px-1 rounded">X-Tenant-Id</code>, and lists/KPIs are scoped to it.
      </div>

      <Link
        to="/app/audit"
        className="flex items-start gap-3 rounded-xl border border-border/80 bg-secondary/25 px-4 py-3 text-sm hover:bg-secondary/40 transition-colors max-w-lg"
      >
        <ScrollText className="h-5 w-5 text-primary shrink-0 mt-0.5" />
        <div>
          <p className="font-medium text-foreground">View Audit Trail</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Opens the governed audit log for important system actions (requires reviewer or admin role).
          </p>
        </div>
      </Link>

      {error && (
        <div className="rounded-xl border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm flex items-start gap-2">
          <AlertCircle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {isViewer && (
        <p className="text-xs text-muted-foreground border border-border/60 rounded-lg px-3 py-2 bg-secondary/30">
          Viewer mode: ingestion and review actions are disabled. Choose <strong>Admin</strong> or <strong>Reviewer</strong> to make changes.
        </p>
      )}
      {role === "reviewer" && (
        <p className="text-xs text-muted-foreground border border-border/60 rounded-lg px-3 py-2 bg-secondary/30">
          Reviewers can approve, reject, and send rules back for review. Only <strong>Admin</strong> can publish rules.
        </p>
      )}

      <div className="grid md:grid-cols-3 gap-4">
        {[
          {
            icon: Database,
            label: "Indexed sources",
            value: summary ? String(summary.total_sources) : "—",
            sub: summary ? `${summary.failed_sources} failed` : undefined,
          },
          {
            icon: Tag,
            label: "Rules in review",
            value: summary ? String(summary.rules_in_review) : "—",
            sub: summary ? `${summary.published_rules} published` : undefined,
          },
          {
            icon: Shield,
            label: "Avg confidence",
            value: summary ? `${Math.round(summary.avg_confidence * 100)}%` : "—",
            sub: summary
              ? `LLM ${summary.llm_enabled ? "on" : "off"} · ${summary.retrieval_mode}`
              : undefined,
          },
        ].map((k) => (
          <div key={k.label} className="rounded-2xl glass p-5 flex items-center gap-4">
            <div className="h-10 w-10 rounded-xl bg-secondary border border-border flex items-center justify-center">
              <k.icon className="h-4 w-4 text-primary" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">{k.label}</p>
              <p className="text-2xl font-bold">{loading && !summary ? "…" : k.value}</p>
              {k.sub && <p className="text-[10px] text-muted-foreground mt-0.5">{k.sub}</p>}
            </div>
          </div>
        ))}
      </div>

      {cacheMetrics && !isViewer && (
        <div className="rounded-2xl glass overflow-hidden border border-border/70">
          <div className="p-5 border-b border-border flex flex-wrap items-start justify-between gap-3">
            <div className="flex items-start gap-3 min-w-0">
              <div className="h-10 w-10 rounded-xl bg-secondary border border-border flex items-center justify-center shrink-0">
                <Gauge className="h-4 w-4 text-primary" />
              </div>
              <div className="min-w-0">
                <h2 className="text-base font-semibold">Enforcement cache</h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  In-process TTL caches for rule applicability lookups and validate-submission responses (cleared on coarse rule or source changes).
                </p>
                <p className="text-[11px] text-muted-foreground mt-1">
                  Cache stats are process-level; cache keys include tenant but counters are global.
                </p>
              </div>
            </div>
            {canPublish ? (
              <Button
                variant="outline"
                size="sm"
                className="shrink-0"
                disabled={busy === "cache-clear"}
                onClick={() => void onClearCache()}
              >
                {busy === "cache-clear" ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5 mr-1.5" />}
                Clear all
              </Button>
            ) : (
              <p className="text-[11px] text-muted-foreground shrink-0">
                Admin-only: full cache clear.
              </p>
            )}
          </div>
          <div className="p-5 grid sm:grid-cols-2 gap-4">
            {(["rule_lookup", "validation"] as const).map((ns) => {
              const n = cacheMetrics.namespaces[ns];
              if (!n) return null;
              return (
                <div key={ns} className="rounded-xl bg-secondary/30 border border-border/60 p-4">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-3">
                    {ns.replace(/_/g, " ")}
                  </p>
                  <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
                    <dt className="text-muted-foreground">Hits</dt>
                    <dd className="font-mono text-right">{n.hits}</dd>
                    <dt className="text-muted-foreground">Misses</dt>
                    <dd className="font-mono text-right">{n.misses}</dd>
                    <dt className="text-muted-foreground">Current size</dt>
                    <dd className="font-mono text-right">{n.current_size}</dd>
                    <dt className="text-muted-foreground">Sets / invalidations</dt>
                    <dd className="font-mono text-right">
                      {n.sets} / {n.invalidations}
                    </dd>
                  </dl>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {canonicalReport && !isViewer && (
        <div className="rounded-2xl glass overflow-hidden border border-border/70">
          <div className="p-5 border-b border-border flex flex-wrap items-start justify-between gap-3">
            <div className="flex items-start gap-3 min-w-0">
              <div className="h-10 w-10 rounded-xl bg-secondary border border-border flex items-center justify-center shrink-0">
                <Layers className="h-4 w-4 text-primary" />
              </div>
              <div className="min-w-0">
                <h2 className="text-base font-semibold">Canonical Data Health</h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Normalized jurisdiction, program variant, and rejection link coverage versus legacy JSON fields.
                </p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 shrink-0">
              <Button
                variant="outline"
                size="sm"
                disabled={!!busy || isViewer}
                onClick={() => void runCanonicalBackfill(true)}
              >
                {busy === "canonical-dry" ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
                Dry Run Backfill
              </Button>
              {canPublish ? (
                <Button
                  variant="hero"
                  size="sm"
                  disabled={!!busy || isViewer}
                  onClick={() => void runCanonicalBackfill(false)}
                >
                  {busy === "canonical-apply" ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
                  Apply Backfill
                </Button>
              ) : (
                <span className="text-[11px] text-muted-foreground self-center">Apply: admin only</span>
              )}
            </div>
          </div>
          <div className="p-5 grid sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
            <div className="rounded-lg bg-secondary/30 border border-border/60 px-3 py-2">
              <p className="text-muted-foreground text-[10px] uppercase mb-1">Total rules</p>
              <p className="font-mono text-lg font-semibold">{canonicalReport.total_rules}</p>
            </div>
            <div className="rounded-lg bg-secondary/30 border border-border/60 px-3 py-2">
              <p className="text-muted-foreground text-[10px] uppercase mb-1">Missing jurisdiction FK</p>
              <p className="font-mono text-lg font-semibold">{canonicalReport.rules_missing_jurisdiction_id}</p>
            </div>
            <div className="rounded-lg bg-secondary/30 border border-border/60 px-3 py-2">
              <p className="text-muted-foreground text-[10px] uppercase mb-1">Missing program-variant FK</p>
              <p className="font-mono text-lg font-semibold">{canonicalReport.rules_missing_program_variant_ref_id}</p>
            </div>
            <div className="rounded-lg bg-secondary/30 border border-border/60 px-3 py-2">
              <p className="text-muted-foreground text-[10px] uppercase mb-1">Rejection map, no links</p>
              <p className="font-mono text-lg font-semibold">{canonicalReport.rules_with_rejection_map_but_no_links}</p>
            </div>
          </div>
          <div className="px-5 pb-3 flex flex-wrap gap-3 text-[11px] text-muted-foreground">
            <span className="font-semibold text-foreground/90">Review status:</span>
            {Object.entries(canonicalReport.rules_by_review_status).map(([k, v]) => (
              <span key={k}>
                <span className="font-mono">{k}</span>: {v}
              </span>
            ))}
          </div>
          {lastCanonicalBackfill && (
            <div className="border-t border-border px-5 py-4 space-y-2">
              <p className="text-xs font-semibold">
                Last backfill ({lastCanonicalBackfill.dry_run ? "dry run" : "applied"}) · {lastCanonicalBackfill.changes.length} change records ·{" "}
                <span className="font-mono text-muted-foreground">{JSON.stringify(lastCanonicalBackfill.summary)}</span>
              </p>
              <p className="text-[11px] text-muted-foreground">Sample (first 10 rows):</p>
              <ul className="text-[11px] font-mono space-y-1 max-h-40 overflow-y-auto rounded-md bg-muted/40 p-2">
                {(lastCanonicalBackfill.changes ?? []).slice(0, 10).map((c, i) => (
                  <li key={i} className="break-all">
                    {JSON.stringify(c)}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {governanceConfig && !isViewer && (
        <div className="rounded-2xl glass overflow-hidden border border-border/70">
          <div className="p-5 border-b border-border flex items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className="h-10 w-10 rounded-xl bg-secondary border border-border flex items-center justify-center shrink-0">
                <Gavel className="h-4 w-4 text-primary" />
              </div>
              <div>
                <h2 className="text-base font-semibold">Publish Governance</h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Strict mode can block publish on missing governance fields while still allowing readiness previews.
                </p>
              </div>
            </div>
            <Link
              to="/app/review"
              className="text-xs text-primary hover:underline shrink-0"
            >
              Open Review Queue
            </Link>
          </div>
          <div className="p-5 grid sm:grid-cols-2 gap-4 text-sm">
            <div className="rounded-xl bg-secondary/30 border border-border/60 p-4">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-1">
                STRICT_PUBLISH_CHECKS
              </p>
              <p className="font-mono text-lg font-semibold">
                {governanceConfig.strict_publish_checks ? "true" : "false"}
              </p>
            </div>
            <div className="rounded-xl bg-secondary/30 border border-border/60 p-4">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-1">
                MIN_PUBLISH_CONFIDENCE
              </p>
              <p className="font-mono text-lg font-semibold">
                {governanceConfig.min_publish_confidence.toFixed(2)}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Source onboarding */}
          <div className="rounded-2xl glass overflow-hidden">
            <div className="p-5 border-b border-border">
              <h2 className="text-base font-semibold">Source onboarding</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Ingest official URLs, PDFs, or run the curated YAML batch — same APIs as Sources.
              </p>
            </div>
            <div className="p-5 space-y-5">
              <div className="grid sm:grid-cols-2 gap-3">
                <div>
                  <Label className="text-[10px] uppercase text-muted-foreground">State</Label>
                  <Select value={urlState || "__"} onValueChange={(v) => setUrlState(v === "__" ? "" : v)}>
                    <SelectTrigger className="mt-1">
                      <SelectValue placeholder="Optional" />
                    </SelectTrigger>
                    <SelectContent className="max-h-60">
                      <SelectItem value="__">Any / not set</SelectItem>
                      {taxStates.map((s) => (
                        <SelectItem key={s.abbreviation} value={s.name}>
                          {s.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-[10px] uppercase text-muted-foreground">Tax category</Label>
                  <Select value={urlTax || "__"} onValueChange={(v) => setUrlTax(v === "__" ? "" : (v as TaxType))}>
                    <SelectTrigger className="mt-1">
                      <SelectValue placeholder="Optional" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__">Any / not set</SelectItem>
                      {TAX_TYPES.map((t) => (
                        <SelectItem key={t.value} value={t.value}>
                          {t.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <form onSubmit={onIngestUrl} className="space-y-3">
                <div>
                  <Label className="text-[10px] uppercase text-muted-foreground flex items-center gap-1">
                    <Link2 className="h-3 w-3" /> Official URL
                  </Label>
                  <Input
                    className="mt-1"
                    placeholder="https://…"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    disabled={isViewer}
                  />
                </div>
                <div className="grid sm:grid-cols-3 gap-2">
                  <div className="sm:col-span-2">
                    <Label className="text-[10px] uppercase text-muted-foreground">Title (optional)</Label>
                    <Input className="mt-1" value={urlTitle} onChange={(e) => setUrlTitle(e.target.value)} disabled={isViewer} />
                  </div>
                  <div>
                    <Label className="text-[10px] uppercase text-muted-foreground">Crawl depth</Label>
                    <Select value={crawlDepth} onValueChange={setCrawlDepth} disabled={isViewer}>
                      <SelectTrigger className="mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {["0", "1", "2", "3"].map((d) => (
                          <SelectItem key={d} value={d}>
                            {d}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2 items-end">
                  <div className="w-28">
                    <Label className="text-[10px] uppercase text-muted-foreground">Max pages</Label>
                    <Input className="mt-1" value={crawlMax} onChange={(e) => setCrawlMax(e.target.value)} disabled={isViewer} />
                  </div>
                  <Button type="submit" variant="hero" disabled={isViewer || busy === "url" || !url.trim()}>
                    {busy === "url" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4 mr-1" />}
                    Run ingestion
                  </Button>
                  <Button type="button" variant="outline" disabled={isViewer || !!busy} onClick={() => fileRef.current?.click()}>
                    {busy === "upload" ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileUp className="h-4 w-4 mr-1" />}
                    Upload file
                  </Button>
                  <input
                    ref={fileRef}
                    type="file"
                    accept=".pdf,.txt,.html,.htm"
                    className="hidden"
                    onChange={(e) => void onUpload(e.target.files?.[0] ?? null)}
                  />
                  <Button type="button" variant="secondary" disabled={isViewer || busy === "yaml"} onClick={() => void onYamlRun()}>
                    {busy === "yaml" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Database className="h-4 w-4 mr-1" />}
                    Run YAML seed
                  </Button>
                </div>
              </form>
            </div>
          </div>

          {/* Publishing */}
          <div className="rounded-2xl glass overflow-hidden">
            <div className="p-5 border-b border-border flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold">Publishing & review</h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Filter rules by review status. Approve / reject / send back / publish (publish: admins only).
                </p>
              </div>
              <Select
                value={rulesFilter || "__all__"}
                onValueChange={(v) => setRulesFilter(v === "__all__" ? "" : v)}
              >
                <SelectTrigger className="w-[200px] h-9">
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">All (latest)</SelectItem>
                  {(taxonomy?.review_statuses ?? []).map((s) => (
                    <SelectItem key={s} value={s}>
                      {s.replace(/_/g, " ")}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="divide-y divide-border/40 max-h-[420px] overflow-y-auto">
              {rules.length === 0 && (
                <p className="p-5 text-sm text-muted-foreground">No rules match this filter yet. Ingest sources and extract rules first.</p>
              )}
              {rules.map((r) => (
                <div key={r.id} className="p-4 flex flex-wrap gap-3 items-start justify-between hover:bg-secondary/20">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium line-clamp-2">{r.rule_title}</p>
                    <p className="text-[11px] text-muted-foreground mt-1">
                      {r.state} · {taxTypeLabel(r.tax_category)} ·{" "}
                      <span className="font-mono">{r.review_status}</span> · {Math.round(r.confidence_score * 100)}%
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-1 shrink-0">
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-8 text-xs"
                      disabled={isViewer || busy?.startsWith("act-")}
                      onClick={() => void reviewAct(r.id, "needs_review")}
                    >
                      Review
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-8 text-xs"
                      disabled={isViewer || busy?.startsWith("act-")}
                      onClick={() => void reviewAct(r.id, "approve")}
                    >
                      Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-8 text-xs text-destructive border-destructive/30"
                      disabled={isViewer || busy?.startsWith("act-")}
                      onClick={() => void reviewAct(r.id, "reject")}
                    >
                      Reject
                    </Button>
                    <Button
                      size="sm"
                      variant="hero"
                      className="h-8 text-xs"
                      disabled={isViewer || !canPublish || busy?.startsWith("act-")}
                      onClick={() => void reviewAct(r.id, "publish")}
                    >
                      Publish
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Taxonomy + RBAC blurb */}
        <div className="space-y-6">
          <div className="rounded-2xl glass p-5">
            <h2 className="text-base font-semibold mb-1">Taxonomy</h2>
            <p className="text-xs text-muted-foreground mb-4">
              Canonical values from the backend (aligned with rule validation).
            </p>
            <div className="space-y-3 max-h-[360px] overflow-y-auto pr-1">
              <div className="rounded-lg bg-secondary/40 border border-border/60 p-3">
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-2">States</p>
                <p className="text-xs text-muted-foreground">{taxStates.length} jurisdictions (full names in selects)</p>
              </div>
              <div className="rounded-lg bg-secondary/40 border border-border/60 p-3">
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-2">Tax categories</p>
                <div className="flex flex-wrap gap-1.5">
                  {cats.map((i) => (
                    <span key={i} className="text-[11px] px-2 py-0.5 rounded bg-secondary border border-border">
                      {i.replace(/_/g, " ")}
                    </span>
                  ))}
                </div>
              </div>
              <div className="rounded-lg bg-secondary/40 border border-border/60 p-3">
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-2">Workflow stages</p>
                <div className="flex flex-wrap gap-1.5">
                  {stages.map((i) => (
                    <span key={i} className="text-[11px] px-2 py-0.5 rounded bg-secondary border border-border">
                      {i.replace(/_/g, " ")}
                    </span>
                  ))}
                </div>
              </div>
              <div className="rounded-lg bg-secondary/40 border border-border/60 p-3">
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-2">Source types</p>
                <div className="flex flex-wrap gap-1.5">
                  {srcTypes.map((i) => (
                    <span key={i} className="text-[11px] px-2 py-0.5 rounded bg-secondary border border-border font-mono">
                      {i}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-2xl glass p-5 border border-dashed border-border">
            <h2 className="text-base font-semibold mb-1">RBAC</h2>
            <p className="text-xs text-muted-foreground">
              Real authentication is not wired yet. The session role above is stored in <code className="text-[10px] bg-secondary px-1 rounded">localStorage</code> and sent as{" "}
              <code className="text-[10px] bg-secondary px-1 rounded">actor</code> on review actions so the audit trail reflects who performed each step.
            </p>
            {summary?.extraction_breakdown && Object.keys(summary.extraction_breakdown).length > 0 && (
              <div className="mt-3 text-[11px] text-muted-foreground">
                <span className="font-semibold text-foreground">Extractions: </span>
                {Object.entries(summary.extraction_breakdown)
                  .map(([k, v]) => `${k || "unknown"}: ${v}`)
                  .join(" · ")}
              </div>
            )}
            {summary?.last_ingestion_run && (
              <p className="mt-2 text-[11px] text-muted-foreground">
                Last run: <span className="font-mono">{summary.last_ingestion_run.id.slice(0, 8)}</span> ({summary.last_ingestion_run.status}) —{" "}
                {timeAgo(summary.last_ingestion_run.started_at)}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Audit log */}
      <div className="rounded-2xl glass">
        <div className="p-5 border-b border-border flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-primary" />
            <h2 className="text-base font-semibold">Review audit log</h2>
            <span className="text-xs text-muted-foreground">(from <code className="bg-secondary px-1 rounded text-[10px]">review_events</code>)</span>
          </div>
          <Button variant="outline" size="sm" onClick={exportAuditCsv} disabled={audit.length === 0}>
            Export CSV
          </Button>
        </div>
        <div className="max-h-[380px] overflow-y-auto">
          {audit.length === 0 && (
            <p className="p-5 text-sm text-muted-foreground">No review events yet. Approve or edit a rule to populate the trail.</p>
          )}
          {audit.map((a) => (
            <div
              key={a.id}
              className="flex flex-wrap items-center gap-x-4 gap-y-1 px-5 py-3 border-t border-border/40 text-sm hover:bg-secondary/20"
            >
              <span className="font-medium w-28 truncate text-xs">{a.actor || "—"}</span>
              <span className="text-muted-foreground flex-1 min-w-[200px]">
                {auditSummaryLine(a)} · <span className="text-foreground/90">{a.rule_title.slice(0, 80)}{a.rule_title.length > 80 ? "…" : ""}</span>
              </span>
              <span className="text-[10px] font-mono text-muted-foreground hidden md:inline">{a.rule_id.slice(0, 8)}…</span>
              <span className="text-xs text-muted-foreground w-24 text-right">{timeAgo(a.created_at)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Admin;
