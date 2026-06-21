import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AlertCircle, Loader2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { AnalyticsResponse, api } from "@/lib/api";

const tooltipStyle = {
  backgroundColor: "hsl(var(--popover))",
  border: "1px solid hsl(var(--border))",
  borderRadius: "0.75rem",
  fontSize: "12px",
  padding: "8px 12px",
};

const PIE_COLORS = [
  "hsl(var(--primary))",
  "hsl(var(--teal))",
  "hsl(var(--success))",
  "hsl(var(--warning))",
  "hsl(var(--muted-foreground))",
  "hsl(var(--destructive))",
];

function methodLabel(m: string): string {
  const map: Record<string, string> = {
    llm: "LLM",
    heuristic: "Heuristic",
    manual: "Manual",
    seed_demo: "Seed / demo",
    other: "Other",
    unknown: "Unknown",
  };
  return map[m] ?? m;
}

const Analytics = () => {
  const [days, setDays] = useState(30);
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    api
      .analytics(days)
      .then(setData)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : String(e)),
      )
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days]);

  const timeline = useMemo(() => {
    if (!data) return [];
    return data.rules_created_by_day.map((r, i) => ({
      date: r.date.slice(5),
      fullDate: r.date,
      rules: r.count,
      review_actions: data.review_events_by_day[i]?.count ?? 0,
    }));
  }, [data]);

  const sourcesByStatusRows = useMemo(() => {
    if (!data) return [];
    return Object.entries(data.sources_by_status).map(([status, count]) => ({
      status: status.replace(/_/g, " "),
      count,
    }));
  }, [data]);

  const extractionPie = useMemo(() => {
    if (!data) return [];
    return data.extraction_methods.map((row) => ({
      ...row,
      name: methodLabel(row.method),
    }));
  }, [data]);

  const s = data?.summary;

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-[1600px]">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="app-label">Insights</p>
          <h1 className="font-serif text-3xl leading-tight tracking-tight mt-1">Analytics</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Operational metrics from indexed sources and rules (no mock samples).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={String(days)} onValueChange={(v) => setDays(Number(v))}>
            <SelectTrigger className="w-[140px] h-9">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">Last 7 days</SelectItem>
              <SelectItem value="30">Last 30 days</SelectItem>
              <SelectItem value="90">Last 90 days</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`h-3.5 w-3.5 mr-1 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm flex items-center gap-2 text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {loading && !data && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground py-12 justify-center">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading analytics…
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              {
                label: "Total rules",
                value: s?.total_rules.toLocaleString() ?? "—",
                hint: `${s?.published_rules ?? 0} published`,
              },
              {
                label: "Sources",
                value: s?.total_sources.toLocaleString() ?? "—",
                hint: `${s?.rules_in_review ?? 0} rules in review`,
              },
              {
                label: `Rules created (${data.window_days}d window)`,
                value: s?.rules_created_in_window.toLocaleString() ?? "—",
                hint: "From rule created_at timestamps",
              },
              {
                label: `Review actions (${data.window_days}d)`,
                value: s?.review_events_in_window.toLocaleString() ?? "—",
                hint: `${s?.source_content_changes_in_window ?? 0} source checksum changes`,
              },
            ].map((k) => (
              <div key={k.label} className="rounded-2xl glass p-5">
                <p className="text-xs text-muted-foreground">{k.label}</p>
                <p className="text-2xl font-bold mt-2">{k.value}</p>
                <p className="text-[11px] text-muted-foreground mt-1">{k.hint}</p>
              </div>
            ))}
          </div>

          <div className="grid lg:grid-cols-2 gap-6">
            <div className="rounded-2xl glass p-6">
              <div className="mb-4">
                <h3 className="text-base font-semibold">Rules by state</h3>
                <p className="text-xs text-muted-foreground">Current indexed corpus</p>
              </div>
              {data.rules_by_state.length === 0 ? (
                <p className="text-sm text-muted-foreground py-12 text-center">No rules yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart
                    layout="vertical"
                    data={data.rules_by_state}
                    margin={{ left: 8, right: 16, top: 8, bottom: 8 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                    <XAxis type="number" stroke="hsl(var(--muted-foreground))" fontSize={11} tickLine={false} />
                    <YAxis
                      type="category"
                      dataKey="state"
                      width={100}
                      stroke="hsl(var(--muted-foreground))"
                      fontSize={10}
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Bar dataKey="count" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} name="Rules" />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>

            <div className="rounded-2xl glass p-6">
              <div className="mb-4">
                <h3 className="text-base font-semibold">Rules by tax category</h3>
                <p className="text-xs text-muted-foreground">Normalized categories</p>
              </div>
              {data.rules_by_tax_category.length === 0 ? (
                <p className="text-sm text-muted-foreground py-12 text-center">No rules yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart data={data.rules_by_tax_category}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                    <XAxis
                      dataKey="category"
                      stroke="hsl(var(--muted-foreground))"
                      fontSize={10}
                      tickLine={false}
                      axisLine={false}
                      interval={0}
                      angle={-25}
                      textAnchor="end"
                      height={70}
                    />
                    <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} tickLine={false} axisLine={false} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Bar dataKey="count" fill="hsl(var(--teal))" radius={[4, 4, 0, 0]} name="Rules" />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>

            <div className="rounded-2xl glass p-6">
              <div className="mb-4">
                <h3 className="text-base font-semibold">Confidence distribution</h3>
                <p className="text-xs text-muted-foreground">Across all rules today</p>
              </div>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={data.confidence_distribution}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                  <XAxis dataKey="label" stroke="hsl(var(--muted-foreground))" fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="count" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} name="Rules" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="rounded-2xl glass p-6">
              <div className="mb-4">
                <h3 className="text-base font-semibold">Ingestion outcomes</h3>
                <p className="text-xs text-muted-foreground">Sources by processing status</p>
              </div>
              {sourcesByStatusRows.length === 0 ? (
                <p className="text-sm text-muted-foreground py-12 text-center">No sources yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={sourcesByStatusRows}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                    <XAxis dataKey="status" stroke="hsl(var(--muted-foreground))" fontSize={10} tickLine={false} axisLine={false} />
                    <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} tickLine={false} axisLine={false} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Bar dataKey="count" fill="hsl(var(--success))" radius={[4, 4, 0, 0]} name="Sources" />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>

            <div className="rounded-2xl glass p-6">
              <div className="mb-4">
                <h3 className="text-base font-semibold">Extraction method</h3>
                <p className="text-xs text-muted-foreground">LLM · heuristic · manual · seed/demo · other</p>
              </div>
              {extractionPie.length === 0 || extractionPie.every((x) => x.count === 0) ? (
                <p className="text-sm text-muted-foreground py-12 text-center">No extraction breakdown.</p>
              ) : (
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={extractionPie}
                      dataKey="count"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={56}
                      outerRadius={96}
                      paddingAngle={2}
                    >
                      {extractionPie.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} stroke="transparent" />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={tooltipStyle} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>

            <div className="rounded-2xl glass p-6">
              <div className="mb-4">
                <h3 className="text-base font-semibold">Source freshness</h3>
                <p className="text-xs text-muted-foreground">Time since last_checked on each source</p>
              </div>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={data.source_freshness}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                  <XAxis dataKey="label" stroke="hsl(var(--muted-foreground))" fontSize={10} tickLine={false} axisLine={false} />
                  <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="count" fill="hsl(var(--warning))" radius={[4, 4, 0, 0]} name="Sources" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="rounded-2xl glass p-6 lg:col-span-2">
              <div className="mb-4">
                <h3 className="text-base font-semibold">Activity over time</h3>
                <p className="text-xs text-muted-foreground">
                  Rules created per day vs review audit actions (same {data.window_days}-day window)
                </p>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={timeline}>
                  <defs>
                    <linearGradient id="rulesGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.45} />
                      <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="hsl(var(--teal))" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="hsl(var(--teal))" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                  <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" fontSize={10} tickLine={false} axisLine={false} />
                  <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Area
                    type="monotone"
                    dataKey="review_actions"
                    name="Review actions"
                    stroke="hsl(var(--teal))"
                    strokeWidth={2}
                    fill="url(#revGrad)"
                  />
                  <Area
                    type="monotone"
                    dataKey="rules"
                    name="Rules created"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2}
                    fill="url(#rulesGrad)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default Analytics;
