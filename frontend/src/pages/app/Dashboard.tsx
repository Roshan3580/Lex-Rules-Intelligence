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
  RefreshCw,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { AppPage } from "@/components/app/AppPage";
import { AppSectionHeader } from "@/components/app/AppSectionHeader";
import { AppCard, AppCardHeader } from "@/components/app/AppCard";
import { MetricCard, MetricCardSkeleton } from "@/components/app/MetricCard";
import { EmptyState } from "@/components/app/EmptyState";
import { StatusBadge } from "@/components/app/StatusBadge";
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
      return { Icon: Sparkles, className: "border-primary/20 bg-primary/5 text-primary" };
    case "source_updated":
      return { Icon: GitPullRequest, className: "border-emerald-200 bg-emerald-50 text-emerald-700" };
    case "ingestion_run":
      return { Icon: Database, className: "border-border bg-secondary text-muted-foreground" };
    case "approved":
      return { Icon: CheckCircle2, className: "border-emerald-200 bg-emerald-50 text-emerald-700" };
    case "flagged":
      return { Icon: AlertTriangle, className: "border-amber-200 bg-amber-50 text-amber-700" };
    case "updated":
      return { Icon: GitPullRequest, className: "border-primary/20 bg-primary/5 text-primary" };
    default:
      return { Icon: Clock, className: "border-border bg-secondary text-muted-foreground" };
  }
}

const Dashboard = () => {
  const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
  const [activities, setActivities] = useState<DashboardActivity[]>([]);
  const [alerts, setAlerts] = useState<DashboardAlert[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [monitorBusy, setMonitorBusy] = useState(false);

  const loadDashboard = () => {
    setLoading(true);
    setError(null);
    return Promise.allSettled([api.dashboard(45), api.health()]).then(([d, h]) => {
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
  };

  useEffect(() => {
    void loadDashboard();
  }, []);

  async function onMonitorRun() {
    setMonitorBusy(true);
    setError(null);
    try {
      await api.monitorRun({ limit: 40, auto_extract: true });
      await loadDashboard();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setMonitorBusy(false);
    }
  }

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
    <AppPage>
      <AppSectionHeader
        label="Overview"
        title="State Tax Rules Intelligence"
        description={
          <>
            Source-grounded answers across all 50 U.S. states.
            {health && (
              <span className="mt-1 block">
                Backend: <span className="font-medium text-foreground">{health.status}</span>
                {" · "}
                LLM:{" "}
                <span className="font-medium text-foreground">
                  {health.llm_enabled ? "connected" : "fallback mode"}
                </span>
                {health.demo_mode ? (
                  <>
                    {" · "}
                    <StatusBadge tone="warning">Demo seed on</StatusBadge>
                  </>
                ) : null}
                {kpis && (
                  <>
                    {" · "}
                    Embeddings: <span className="font-mono">{kpis.embedding_provider}</span>
                  </>
                )}
              </span>
            )}
          </>
        }
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              className="h-8 text-xs"
              disabled={monitorBusy || loading}
              onClick={() => void onMonitorRun()}
              title="Re-fetch URL sources and refresh metrics"
            >
              {monitorBusy ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <RefreshCw className="h-3.5 w-3.5" />
              )}
              <span className="ml-1.5 hidden sm:inline">Check sources</span>
            </Button>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Clock className="h-3.5 w-3.5" />}
              <span>{loading ? "Loading…" : "Live"}</span>
            </div>
          </>
        }
      />

      {error && (
        <div className="border border-destructive/30 bg-red-50 px-4 py-3 text-sm text-destructive">
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

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {loading && !kpis
          ? Array.from({ length: 8 }).map((_, i) => <MetricCardSkeleton key={i} />)
          : kpiCards.map((k) => (
              <MetricCard key={k.label} label={k.label} value={k.value} icon={k.icon} />
            ))}
      </div>

      {!loading && kpis && kpis.total_rules === 0 && (
        <AppCard padding="lg">
          <EmptyState
            title="No rules indexed yet"
            description="Add sources or run the seed batch to populate the intelligence layer."
            action={
              <Button asChild variant="outline" size="sm">
                <Link to="/app/sources">Open sources</Link>
              </Button>
            }
          />
        </AppCard>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <AppCard padding="lg" className="lg:col-span-2">
          <AppCardHeader
            title="Activity feed"
            description="Ingestion runs, extractions, source updates, and review actions"
            action={
              <Link to="/app/sources" className="text-xs text-primary hover:underline">
                Sources
              </Link>
            }
          />
          <div className="space-y-1">
            {!loading && activities.length === 0 && (
              <EmptyState description="No activity yet. Ingest a URL or PDF from Sources, or run the YAML seed batch." />
            )}
            {activities.map((a) => {
              const { Icon, className } = activityIcon(a.kind);
              return (
                <div
                  key={a.id}
                  className="flex items-start gap-3 border-b border-border py-3 last:border-0"
                >
                  <div
                    className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center border ${className}`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium leading-snug text-foreground">{a.title}</p>
                    <p className="mt-0.5 line-clamp-2 text-sm leading-snug text-muted-foreground">
                      {a.detail}
                    </p>
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      <span className="max-w-[200px] truncate font-mono text-[11px] text-muted-foreground">
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
        </AppCard>

        <AppCard padding="lg">
          <AppCardHeader
            title="Change alerts"
            description="From live sources and rule quality checks"
            action={
              alerts.length > 0 ? (
                <StatusBadge tone="warning">{alerts.length} open</StatusBadge>
              ) : undefined
            }
          />
          <div className="space-y-3">
            {!loading && alerts.length === 0 && (
              <EmptyState description="No alerts — or nothing to flag yet." />
            )}
            {alerts.map((alertItem) => (
              <div
                key={alertItem.id}
                className="border border-border bg-secondary/40 p-3 transition-colors hover:border-primary/30"
              >
                <div className="flex items-start gap-2">
                  <span
                    className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                      alertItem.severity === "error"
                        ? "bg-destructive"
                        : alertItem.severity === "warning"
                          ? "bg-amber-500"
                          : "bg-primary"
                    }`}
                  />
                  <div>
                    <p className="text-sm font-medium leading-snug">{alertItem.title}</p>
                    <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{alertItem.body}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <Link to="/app/review" className="mt-4 inline-block text-xs text-primary hover:underline">
            Open review queue →
          </Link>
        </AppCard>
      </div>
    </AppPage>
  );
};

export default Dashboard;
