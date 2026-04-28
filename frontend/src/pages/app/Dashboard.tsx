import {
  FileText,
  Database,
  AlertTriangle,
  Sparkles,
  CheckCircle2,
  GitPullRequest,
  Clock,
  Loader2,
  BookCheck,
  AlertCircle,
  Cpu,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Confidence } from "@/components/Confidence";
import {
  api,
  DashboardActivity,
  DashboardAlert,
  DashboardKPIs,
  Health,
} from "@/lib/api";

function timeAgo(iso: string): string {
  const t = new Date(iso).getTime();
  const diff = Date.now() - t;
  if (diff < 60_000) return "just now";
  if (diff < 3_600_000) return `${Math.round(diff / 60_000)}m`;
  if (diff < 86_400_000) return `${Math.round(diff / 3_600_000)}h`;
  return `${Math.round(diff / 86_400_000)}d`;
}

function activityIcon(kind: string) {
  switch (kind) {
    case "extracted":
      return { Icon: Sparkles, className: "bg-primary/15 text-primary" };
    case "source_updated":
      return { Icon: GitPullRequest, className: "bg-teal/15 text-teal" };
    case "ingestion_run":
      return { Icon: Database, className: "bg-secondary text-muted-foreground" };
    case "approved":
      return { Icon: CheckCircle2, className: "bg-success/15 text-success" };
    case "flagged":
      return { Icon: AlertTriangle, className: "bg-warning/15 text-warning" };
    case "updated":
      return { Icon: GitPullRequest, className: "bg-primary/10 text-primary" };
    default:
      return { Icon: Clock, className: "bg-secondary text-muted-foreground" };
  }
}

const Dashboard = () => {
  const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
  const [activities, setActivities] = useState<DashboardActivity[]>([]);
  const [alerts, setAlerts] = useState<DashboardAlert[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.allSettled([api.dashboard(45), api.health()]).then(([d, h]) => {
      if (h.status === "fulfilled") setHealth(h.value);
      if (d.status === "fulfilled") {
        setKpis(d.value.kpis);
        setActivities(d.value.activities);
        setAlerts(d.value.alerts);
      } else {
        setError(
          d.status === "rejected"
            ? d.reason instanceof Error
              ? d.reason.message
              : String(d.reason)
            : "Failed to load dashboard",
        );
      }
      setLoading(false);
    });
  }, []);

  const avgPct = kpis ? Math.round(kpis.avg_confidence * 100) : 0;

  const kpiCards = kpis
    ? [
        { label: "Total rules", value: kpis.total_rules.toLocaleString(), icon: FileText },
        { label: "Sources indexed", value: kpis.total_sources.toLocaleString(), icon: Database },
        { label: "Published rules", value: kpis.published_rules.toLocaleString(), icon: BookCheck },
        { label: "In review queue", value: kpis.rules_in_review.toLocaleString(), icon: GitPullRequest },
        { label: "Avg confidence", value: `${avgPct}%`, icon: Sparkles },
        { label: "Failed ingestions", value: kpis.failed_sources.toLocaleString(), icon: AlertCircle },
        { label: "Retrieval", value: kpis.retrieval_mode, icon: Cpu },
        { label: "Vector index", value: kpis.vector_index_size.toLocaleString(), icon: Database },
      ]
    : [];

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-[1600px]">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <p className="text-xs uppercase tracking-widest text-muted-foreground">Overview</p>
          <h1 className="text-3xl font-bold tracking-tight mt-1">State Tax Rules Intelligence</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Source-grounded answers across all 50 U.S. states.
            {health && (
              <span className="ml-2">
                Backend: <span className="font-medium text-foreground">{health.status}</span>
                {" · "}
                LLM:{" "}
                <span className="font-medium text-foreground">
                  {health.llm_enabled ? "connected" : "fallback mode"}
                </span>
                {health.demo_mode ? (
                  <>
                    {" · "}
                    <span className="text-warning font-medium">Demo seed on</span>
                  </>
                ) : null}
              </span>
            )}
            {kpis && (
              <span className="ml-2 block sm:inline mt-1 sm:mt-0 text-xs">
                Embeddings: <span className="font-mono">{kpis.embedding_provider}</span>
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Clock className="h-3.5 w-3.5" />}
          <span>{loading ? "Loading…" : "Live"}</span>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {kpis?.last_ingestion_run && (
        <p className="text-xs text-muted-foreground">
          Last ingestion run:{" "}
          <span className="font-mono">{kpis.last_ingestion_run.id.slice(0, 8)}</span> ·{" "}
          {kpis.last_ingestion_run.status} · {timeAgo(kpis.last_ingestion_run.started_at)} ago ·{" "}
          {kpis.last_ingestion_run.ingested}/{kpis.last_ingestion_run.total || "—"} ingested
        </p>
      )}

      {/* KPI grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {(loading && !kpis
          ? Array.from({ length: 8 }).map((_, i) => (
              <div
                key={i}
                className="rounded-2xl glass p-5 animate-pulse h-28 bg-secondary/30"
              />
            ))
          : kpiCards.map((k) => (
              <div
                key={k.label}
                className="group relative rounded-2xl glass p-5 hover:border-primary/30 transition-all"
              >
                <div className="flex items-center justify-between">
                  <div className="h-8 w-8 rounded-lg bg-secondary border border-border flex items-center justify-center">
                    <k.icon className="h-4 w-4 text-muted-foreground" />
                  </div>
                </div>
                <p className="mt-4 text-2xl sm:text-3xl font-bold tracking-tight">{k.value}</p>
                <p className="text-xs text-muted-foreground mt-1">{k.label}</p>
              </div>
            )))}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Activity feed */}
        <div className="lg:col-span-2 rounded-2xl glass p-6">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-base font-semibold">Activity feed</h2>
              <p className="text-xs text-muted-foreground">
                Ingestion runs, extractions, source updates, and review actions
              </p>
            </div>
            <Link to="/app/sources" className="text-xs text-primary hover:underline">
              Sources
            </Link>
          </div>
          <div className="space-y-1">
            {!loading && activities.length === 0 && (
              <p className="text-sm text-muted-foreground py-6">
                No activity yet. Ingest a URL or PDF from Sources, or run the YAML seed batch.
              </p>
            )}
            {activities.map((a) => {
              const { Icon, className } = activityIcon(a.kind);
              return (
                <div
                  key={a.id}
                  className="flex items-start gap-3 py-3 border-b border-border/40 last:border-0"
                >
                  <div className={`mt-0.5 h-7 w-7 rounded-lg flex items-center justify-center shrink-0 ${className}`}>
                    <Icon className="h-3.5 w-3.5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground leading-snug">{a.title}</p>
                    <p className="text-sm text-muted-foreground leading-snug mt-0.5 line-clamp-2">
                      {a.detail}
                    </p>
                    <div className="flex flex-wrap items-center gap-2 mt-1">
                      <span className="text-[11px] text-muted-foreground font-mono truncate max-w-[200px]">
                        {a.context}
                      </span>
                      <span className="text-[11px] text-muted-foreground">·</span>
                      <span className="text-[11px] text-muted-foreground">{timeAgo(a.created_at)} ago</span>
                      {a.confidence_pct != null && (
                        <>
                          <span className="text-[11px] text-muted-foreground">·</span>
                          <Confidence value={a.confidence_pct} size="sm" />
                        </>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Alerts */}
        <div className="rounded-2xl glass p-6">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-base font-semibold">Change alerts</h2>
              <p className="text-xs text-muted-foreground">From live sources & rule quality checks</p>
            </div>
            {alerts.length > 0 && (
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-warning/15 text-warning">
                {alerts.length} open
              </span>
            )}
          </div>
          <div className="space-y-3">
            {!loading && alerts.length === 0 && (
              <p className="text-sm text-muted-foreground">No alerts — or nothing to flag yet.</p>
            )}
            {alerts.map((alertItem) => (
              <div
                key={alertItem.id}
                className="rounded-xl border border-border/60 bg-secondary/30 p-3 hover:border-primary/30 transition-colors"
              >
                <div className="flex items-start gap-2">
                  <span
                    className={`mt-1.5 h-1.5 w-1.5 rounded-full shrink-0 ${
                      alertItem.severity === "error"
                        ? "bg-destructive"
                        : alertItem.severity === "warning"
                          ? "bg-warning"
                          : "bg-primary"
                    }`}
                  />
                  <div>
                    <p className="text-sm font-medium leading-snug">{alertItem.title}</p>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{alertItem.body}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <Link
            to="/app/review"
            className="mt-4 inline-block text-xs text-primary hover:underline"
          >
            Open review queue →
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
