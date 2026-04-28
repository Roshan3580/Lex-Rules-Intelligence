import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity,
  Database,
  FileUp,
  Link2,
  Loader2,
  Play,
  RefreshCw,
  Shield,
  Tag,
  AlertCircle,
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
  getAppRole,
  setAppRole,
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

  const fileRef = useRef<HTMLInputElement>(null);
  const [url, setUrl] = useState("");
  const [urlTitle, setUrlTitle] = useState("");
  const [urlState, setUrlState] = useState("");
  const [urlTax, setUrlTax] = useState<TaxType | "">("");
  const [crawlDepth, setCrawlDepth] = useState("0");
  const [crawlMax, setCrawlMax] = useState("5");

  const readonly = role === "readonly";
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
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [rulesFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  const onRoleChange = (v: AppRoleId) => {
    setRole(v);
    setAppRole(v);
  };

  async function onIngestUrl(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim() || readonly) return;
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
    if (!f || readonly) return;
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
    if (readonly) return;
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
    if (readonly) return;
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
          <p className="text-xs uppercase tracking-widest text-muted-foreground">Workspace settings</p>
          <h1 className="text-3xl font-bold tracking-tight mt-1">Admin</h1>
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
                <SelectItem value="readonly">Read-only</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm flex items-start gap-2">
          <AlertCircle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {readonly && (
        <p className="text-xs text-muted-foreground border border-border/60 rounded-lg px-3 py-2 bg-secondary/30">
          Read-only mode: ingestion and review actions are disabled. Choose <strong>Admin</strong> or <strong>Reviewer</strong> to make changes.
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
                    disabled={readonly}
                  />
                </div>
                <div className="grid sm:grid-cols-3 gap-2">
                  <div className="sm:col-span-2">
                    <Label className="text-[10px] uppercase text-muted-foreground">Title (optional)</Label>
                    <Input className="mt-1" value={urlTitle} onChange={(e) => setUrlTitle(e.target.value)} disabled={readonly} />
                  </div>
                  <div>
                    <Label className="text-[10px] uppercase text-muted-foreground">Crawl depth</Label>
                    <Select value={crawlDepth} onValueChange={setCrawlDepth} disabled={readonly}>
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
                    <Input className="mt-1" value={crawlMax} onChange={(e) => setCrawlMax(e.target.value)} disabled={readonly} />
                  </div>
                  <Button type="submit" variant="hero" disabled={readonly || busy === "url" || !url.trim()}>
                    {busy === "url" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4 mr-1" />}
                    Run ingestion
                  </Button>
                  <Button type="button" variant="outline" disabled={readonly || !!busy} onClick={() => fileRef.current?.click()}>
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
                  <Button type="button" variant="secondary" disabled={readonly || busy === "yaml"} onClick={() => void onYamlRun()}>
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
                      disabled={readonly || busy?.startsWith("act-")}
                      onClick={() => void reviewAct(r.id, "needs_review")}
                    >
                      Review
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-8 text-xs"
                      disabled={readonly || busy?.startsWith("act-")}
                      onClick={() => void reviewAct(r.id, "approve")}
                    >
                      Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-8 text-xs text-destructive border-destructive/30"
                      disabled={readonly || busy?.startsWith("act-")}
                      onClick={() => void reviewAct(r.id, "reject")}
                    >
                      Reject
                    </Button>
                    <Button
                      size="sm"
                      variant="hero"
                      className="h-8 text-xs"
                      disabled={readonly || !canPublish || busy?.startsWith("act-")}
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
