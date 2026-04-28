import { FileText, Database, AlertTriangle, Sparkles, CheckCircle2, GitPullRequest, Clock } from "lucide-react";
import { useEffect, useState } from "react";
import { Confidence } from "@/components/Confidence";
import { api, Health, Rule, SourceRow } from "@/lib/api";

const activities = [
  { type: "extracted", text: "New rule extracted from FATF Recommendation 24", source: "fatf.org", time: "2m", conf: 94 },
  { type: "updated", text: "Source updated — PSD2 amendment XV", source: "EUR-Lex", time: "18m", conf: null },
  { type: "flagged", text: "Rule flagged for review — confidence below threshold", source: "AML Directive", time: "1h", conf: 58 },
  { type: "approved", text: "12 rules approved by S. Park", source: "Review Queue", time: "2h", conf: null },
  { type: "extracted", text: "New rule extracted from BaFin circular 09/2026", source: "bafin.de", time: "3h", conf: 88 },
  { type: "flagged", text: "Conflicting rules detected — jurisdiction overlap", source: "Internal", time: "5h", conf: null },
];

const alerts = [
  { title: "PSD2 amendment published", body: "Affects 47 indexed rules across payments program.", severity: "warning" },
  { title: "OFAC SDN list updated", body: "23 new entries. Auto-synced to sanctions workflow.", severity: "info" },
  { title: "Source unreachable: bafin.de", body: "Last successful fetch 6h ago. Auto-retrying.", severity: "error" },
];

const Dashboard = () => {
  const [rules, setRules] = useState<Rule[]>([]);
  const [sources, setSources] = useState<SourceRow[]>([]);
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    Promise.allSettled([api.rules(), api.listSources(), api.health()]).then(
      ([r, s, h]) => {
        if (r.status === "fulfilled") setRules(r.value);
        if (s.status === "fulfilled") setSources(s.value);
        if (h.status === "fulfilled") setHealth(h.value);
      },
    );
  }, []);

  const totalRules = rules.length;
  const reviewQueue = rules.filter((r) =>
    ["draft", "needs_review", "auto_validated"].includes(r.review_status),
  ).length;
  const avgConfidence =
    rules.length === 0
      ? 0
      : Math.round(
          (rules.reduce((s, r) => s + (r.confidence_score || 0), 0) /
            rules.length) *
            100,
        );

  const kpis = [
    { label: "Total rules indexed", value: totalRules.toLocaleString(), icon: FileText },
    { label: "Sources connected", value: sources.length.toLocaleString(), icon: Database },
    { label: "In review queue", value: reviewQueue.toLocaleString(), icon: GitPullRequest },
    { label: "Avg confidence", value: `${avgConfidence}%`, icon: Sparkles },
  ];

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
                {" · "}LLM: <span className="font-medium text-foreground">
                  {health.llm_enabled ? "connected" : "fallback mode"}
                </span>
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Clock className="h-3.5 w-3.5" />
          <span>{health ? "Live" : "Loading…"}</span>
        </div>
      </div>

      {/* KPI grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((k) => (
          <div key={k.label} className="group relative rounded-2xl glass p-5 hover:border-primary/30 transition-all">
            <div className="flex items-center justify-between">
              <div className="h-8 w-8 rounded-lg bg-secondary border border-border flex items-center justify-center">
                <k.icon className="h-4 w-4 text-muted-foreground" />
              </div>
            </div>
            <p className="mt-4 text-3xl font-bold tracking-tight">{k.value}</p>
            <p className="text-xs text-muted-foreground mt-1">{k.label}</p>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Activity feed */}
        <div className="lg:col-span-2 rounded-2xl glass p-6">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-base font-semibold">Activity feed</h2>
              <p className="text-xs text-muted-foreground">Real-time across all sources & workflows</p>
            </div>
            <button className="text-xs text-primary hover:underline">View all</button>
          </div>
          <div className="space-y-1">
            {activities.map((a, i) => (
              <div key={i} className="flex items-start gap-3 py-3 border-b border-border/40 last:border-0">
                <div className={`mt-0.5 h-7 w-7 rounded-lg flex items-center justify-center shrink-0 ${
                  a.type === "extracted" ? "bg-primary/15 text-primary" :
                  a.type === "updated" ? "bg-teal/15 text-teal" :
                  a.type === "flagged" ? "bg-warning/15 text-warning" :
                  "bg-success/15 text-success"
                }`}>
                  {a.type === "extracted" && <Sparkles className="h-3.5 w-3.5" />}
                  {a.type === "updated" && <GitPullRequest className="h-3.5 w-3.5" />}
                  {a.type === "flagged" && <AlertTriangle className="h-3.5 w-3.5" />}
                  {a.type === "approved" && <CheckCircle2 className="h-3.5 w-3.5" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-foreground leading-snug">{a.text}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[11px] text-muted-foreground font-mono">{a.source}</span>
                    <span className="text-[11px] text-muted-foreground">·</span>
                    <span className="text-[11px] text-muted-foreground">{a.time} ago</span>
                    {a.conf !== null && (
                      <>
                        <span className="text-[11px] text-muted-foreground">·</span>
                        <Confidence value={a.conf} size="sm" />
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Alerts */}
        <div className="rounded-2xl glass p-6">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-base font-semibold">Change alerts</h2>
              <p className="text-xs text-muted-foreground">Source & regulatory updates</p>
            </div>
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-warning/15 text-warning">3 NEW</span>
          </div>
          <div className="space-y-3">
            {alerts.map((a) => (
              <div key={a.title} className="rounded-xl border border-border/60 bg-secondary/30 p-3 hover:border-primary/30 transition-colors cursor-pointer">
                <div className="flex items-start gap-2">
                  <span className={`mt-1.5 h-1.5 w-1.5 rounded-full shrink-0 ${
                    a.severity === "error" ? "bg-destructive" :
                    a.severity === "warning" ? "bg-warning" : "bg-primary"
                  }`} />
                  <div>
                    <p className="text-sm font-medium leading-snug">{a.title}</p>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{a.body}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
