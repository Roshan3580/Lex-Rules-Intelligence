import { useEffect, useState } from "react";
import {
  Check,
  X,
  Edit3,
  FileText,
  ChevronRight,
  Loader2,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Confidence } from "@/components/Confidence";
import { api, ApiError, confidenceToPct, getAppRole, PublishReadinessOut, Rule, RuleVersion, taxTypeLabel } from "@/lib/api";

const ReviewQueue = () => {
  const [queue, setQueue] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [versions, setVersions] = useState<RuleVersion[]>([]);
  const [readiness, setReadiness] = useState<PublishReadinessOut | null>(null);
  const [role, setRole] = useState(() => getAppRole());

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.reviewQueue();
      setQueue(data);
      if (data.length > 0 && !data.find((r) => r.id === selectedId)) {
        setSelectedId(data[0].id);
      }
      if (data.length === 0) setSelectedId(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const sync = () => setRole(getAppRole());
    window.addEventListener("rules_intel_app_role", sync);
    return () => window.removeEventListener("rules_intel_app_role", sync);
  }, []);

  const item = queue.find((r) => r.id === selectedId) || queue[0];

  useEffect(() => {
    if (!item) {
      setVersions([]);
      setReadiness(null);
      return;
    }
    let cancelled = false;
    api
      .ruleVersions(item.id)
      .then((v) => {
        if (!cancelled) setVersions(v.slice(0, 12));
      })
      .catch(() => {
        if (!cancelled) setVersions([]);
      });
    return () => {
      cancelled = true;
    };
  }, [item?.id]);

  async function checkReadiness() {
    if (!item) return;
    setBusy(true);
    setError(null);
    try {
      const r = await api.publishReadiness(item.id);
      setReadiness(r);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      setReadiness(null);
    } finally {
      setBusy(false);
    }
  }

  async function act(action: "approve" | "reject" | "publish" | "needs_review") {
    if (!item) return;
    setBusy(true);
    setError(null);
    try {
      await api.reviewAction(item.id, { action });
      setActionMessage(`Rule ${action}d.`);
      setTimeout(() => setActionMessage(null), 2500);
      await load();
    } catch (e: unknown) {
      if (e instanceof ApiError && e.detail && typeof e.detail === "object") {
        const d = e.detail as any;
        if (d?.error === "publish_blocked" && Array.isArray(d?.blockers)) {
          const msgs = d.blockers.map((b: any) => b?.message ?? JSON.stringify(b)).slice(0, 6);
          setError(`Publish blocked: ${msgs.join(" · ")}`);
          await checkReadiness();
        } else {
          setError(e.message);
        }
      } else {
        setError(e instanceof Error ? e.message : String(e));
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* List */}
      <div className="w-full lg:w-[460px] shrink-0 border-r border-border overflow-y-auto">
        <div className="p-5 border-b border-border sticky top-0 bg-background/80 backdrop-blur-xl z-10">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-widest text-muted-foreground">
                Human-in-the-loop
              </p>
              <h1 className="text-2xl font-bold tracking-tight mt-1">
                Review queue
              </h1>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={load}
              disabled={loading}
            >
              {loading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <RefreshCw className="h-3.5 w-3.5" />
              )}
            </Button>
          </div>
          <div className="flex items-center gap-3 mt-3">
            <span className="text-xs px-2 py-1 rounded-md bg-warning/10 text-warning border border-warning/20">
              {queue.length} pending
            </span>
            <span className="text-xs text-muted-foreground">
              draft · auto-validated · needs review
            </span>
          </div>
        </div>

        {error && (
          <div className="m-4 rounded-xl border border-destructive/30 bg-destructive/5 p-3 text-xs flex items-start gap-2">
            <AlertCircle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
            <span className="text-muted-foreground">{error}</span>
          </div>
        )}

        <div>
          {queue.map((q) => {
            const isSel = item && q.id === item.id;
            return (
              <button
                key={q.id}
                onClick={() => setSelectedId(q.id)}
                className={`w-full text-left p-5 border-b border-border/40 hover:bg-secondary/30 transition-colors ${
                  isSel ? "bg-secondary/50 border-l-2 border-l-primary" : ""
                }`}
              >
                <div className="flex items-start justify-between gap-3 mb-2">
                  <p className="text-sm font-medium leading-snug">
                    {q.rule_title}
                  </p>
                  <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
                </div>
                <p className="text-[11px] text-muted-foreground font-mono mb-3 truncate">
                  {q.source_document_name || q.source_url || "internal"}
                </p>
                <div className="flex items-center justify-between">
                  <Confidence value={confidenceToPct(q.confidence_score)} size="sm" />
                  <span className="text-[10px] uppercase tracking-wider font-semibold text-teal">
                    {q.review_status.replace(/_/g, " ")}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-secondary border border-border text-muted-foreground">
                    {q.state}
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-secondary border border-border text-muted-foreground">
                    {taxTypeLabel(q.tax_category)}
                  </span>
                </div>
              </button>
            );
          })}
          {queue.length === 0 && !loading && (
            <div className="p-8 text-center text-sm text-muted-foreground">
              The review queue is empty. Anything new from extraction will show
              up here.
            </div>
          )}
        </div>
      </div>

      {/* Detail */}
      <div className="hidden lg:flex flex-1 flex-col overflow-hidden">
        {!item ? (
          <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
            Select a rule from the queue to review.
          </div>
        ) : (
          <>
            <div className="p-6 border-b border-border">
              <div className="flex items-start justify-between gap-4 mb-3">
                <div className="min-w-0">
                  <p className="text-[11px] uppercase tracking-widest text-muted-foreground mb-1">
                    Extraction · {item.extraction_method || "manual"}
                  </p>
                  <h2 className="text-xl font-semibold leading-snug">
                    {item.rule_title}
                  </h2>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-[11px] px-2 py-0.5 rounded bg-secondary border border-border text-muted-foreground">
                      {item.state}
                    </span>
                    <span className="text-[11px] px-2 py-0.5 rounded bg-secondary border border-border text-muted-foreground">
                      {taxTypeLabel(item.tax_category)}
                    </span>
                    <span className="text-[11px] uppercase tracking-wider font-semibold text-teal">
                      {item.review_status.replace(/_/g, " ")}
                    </span>
                  </div>
                </div>
                <Confidence value={confidenceToPct(item.confidence_score)} />
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <Button
                  variant="hero"
                  size="sm"
                  disabled={busy}
                  onClick={() => act("approve")}
                >
                  <Check className="h-3.5 w-3.5" /> Approve
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  disabled={busy}
                  onClick={() => act("publish")}
                >
                  Publish
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={busy || role === "viewer"}
                  onClick={() => void checkReadiness()}
                >
                  Check readiness
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={busy}
                  onClick={() => act("needs_review")}
                >
                  <Edit3 className="h-3.5 w-3.5" /> Needs review
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-destructive hover:text-destructive"
                  disabled={busy}
                  onClick={() => act("reject")}
                >
                  <X className="h-3.5 w-3.5" /> Reject
                </Button>
                {actionMessage && (
                  <span className="text-xs text-success ml-2">{actionMessage}</span>
                )}
                <p className="text-[10px] text-muted-foreground w-full mt-2 leading-relaxed">
                  <strong className="text-foreground/80">Governance:</strong> Approve
                  first, then Publish. Publishing requires passing validation,
                  confidence ≥ 70%, and an explicit approval (engineer brief §8).
                </p>
                {readiness && (
                  <div className="w-full mt-2 text-[11px] text-muted-foreground">
                    <span className="font-semibold text-foreground/90">Readiness:</span>{" "}
                    {readiness.can_publish
                      ? "Ready"
                      : readiness.strict_mode_enabled && readiness.blockers.length > 0
                        ? "Blocked"
                        : readiness.blockers.length > 0
                          ? "Would fail strict mode"
                          : readiness.warnings.length > 0
                            ? "Warnings"
                            : "Not ready"}
                    {readiness.blockers.length > 0 && (
                      <span className="ml-2 text-destructive">
                        {readiness.blockers.length} blocker(s)
                      </span>
                    )}
                    {readiness.warnings.length > 0 && (
                      <span className="ml-2 text-warning">
                        {readiness.warnings.length} warning(s)
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>

            <div className="flex-1 grid grid-cols-2 overflow-hidden">
              {/* Source snippet */}
              <div className="border-r border-border overflow-y-auto p-6">
                <div className="flex items-center gap-2 mb-4">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  <p className="text-xs font-mono text-muted-foreground truncate">
                    {item.source_document_name ||
                      item.source_url ||
                      "internal"}
                  </p>
                </div>
                <div className="rounded-xl border border-border bg-card/60 p-5 space-y-3">
                  {item.source_snippet ? (
                    <p className="text-xs text-foreground/80 leading-relaxed whitespace-pre-wrap">
                      {item.source_snippet}
                    </p>
                  ) : (
                    <p className="text-xs text-muted-foreground italic">
                      No source snippet captured for this rule.
                    </p>
                  )}
                  {item.source_url && (
                    <Button variant="outline" size="sm" asChild>
                      <a
                        href={item.source_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open original source
                      </a>
                    </Button>
                  )}
                </div>
              </div>

              {/* Extracted */}
              <div className="overflow-y-auto p-6 bg-secondary/20">
                <p className="text-xs uppercase tracking-wider text-primary font-semibold mb-4 flex items-center gap-1.5">
                  Extracted rule
                </p>
                <div className="space-y-5">
                  <ListBlock label="Summary">{item.rule_summary}</ListBlock>
                  {item.detailed_rule && (
                    <ListBlock label="Detail">{item.detailed_rule}</ListBlock>
                  )}
                  <ChipBlock
                    label="Conditions"
                    items={item.conditions}
                    dotClass="bg-teal"
                  />
                  <ChipBlock
                    label="Required actions"
                    items={item.required_actions}
                    dotClass="bg-primary"
                  />
                  <ChipBlock
                    label="Required forms"
                    items={item.required_forms}
                    dotClass="bg-accent"
                  />
                  <ChipBlock
                    label="Deadlines"
                    items={item.deadlines}
                    dotClass="bg-warning"
                  />
                  <ChipBlock
                    label="Exceptions"
                    items={item.exceptions}
                    dotClass="bg-warning"
                  />

                  {(item.workflow_stage ||
                    item.program_variant ||
                    item.effective_date ||
                    item.effective_date_end ||
                    item.submission_method) && (
                    <div className="rounded-xl border border-border/60 bg-card/40 p-4 space-y-2">
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
                        Program &amp; lifecycle (brief §6)
                      </p>
                      {item.workflow_stage && (
                        <p className="text-xs">
                          <span className="text-muted-foreground">Workflow stage:</span>{" "}
                          {item.workflow_stage}
                        </p>
                      )}
                      {item.submission_method && (
                        <p className="text-xs">
                          <span className="text-muted-foreground">Submission method:</span>{" "}
                          {item.submission_method.replace(/_/g, " ")}
                        </p>
                      )}
                      {(item.effective_date || item.effective_date_end) && (
                        <p className="text-xs">
                          <span className="text-muted-foreground">Effective:</span>{" "}
                          {item.effective_date ?? "—"}
                          {" → "}
                          {item.effective_date_end ?? "—"}
                        </p>
                      )}
                      {item.program_variant &&
                        Object.keys(item.program_variant).length > 0 && (
                          <pre className="text-[10px] font-mono whitespace-pre-wrap break-all bg-secondary/40 rounded-lg p-2 max-h-28 overflow-y-auto">
                            {JSON.stringify(item.program_variant, null, 2)}
                          </pre>
                        )}
                    </div>
                  )}

                  {versions.length > 0 && (
                    <div className="rounded-xl border border-border/60 bg-card/30 p-4">
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-2">
                        Version history ({versions.length})
                      </p>
                      <ul className="space-y-2 max-h-36 overflow-y-auto">
                        {versions.map((v) => (
                          <li key={v.id} className="text-[11px] leading-snug">
                            <span className="font-mono text-primary">v{v.version}</span>
                            {v.captured_reason && (
                              <span className="text-muted-foreground">
                                {" "}
                                · {v.captured_reason}
                              </span>
                            )}
                            <span className="text-muted-foreground block text-[10px]">
                              {new Date(v.created_at).toLocaleString()}
                              {v.actor ? ` · ${v.actor}` : ""}
                            </span>
                            {v.changed_fields && v.changed_fields.length > 0 && (
                              <span className="text-[10px] text-muted-foreground">
                                Δ {v.changed_fields.slice(0, 6).join(", ")}
                                {v.changed_fields.length > 6 ? "…" : ""}
                              </span>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {item.confidence_score < 0.65 && (
                    <div className="rounded-xl border border-warning/30 bg-warning/5 p-4">
                      <p className="text-xs font-semibold text-warning mb-1">
                        Why low confidence?
                      </p>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        Heuristic extraction emitted this rule based on
                        keyword and structural cues. Verify the conditions,
                        deadlines, and forms against the original source
                        before approving.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

function ListBlock({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5 font-semibold">
        {label}
      </p>
      <p className="text-sm whitespace-pre-wrap">{children}</p>
    </div>
  );
}

function ChipBlock({
  label,
  items,
  dotClass,
}: {
  label: string;
  items?: string[] | null;
  dotClass: string;
}) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5 font-semibold">
        {label}
      </p>
      <ul className="space-y-1.5">
        {items.map((c, i) => (
          <li key={`${c}-${i}`} className="text-sm flex items-start gap-2">
            <span
              className={`mt-1.5 h-1 w-1 rounded-full shrink-0 ${dotClass}`}
            />
            {c}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default ReviewQueue;
