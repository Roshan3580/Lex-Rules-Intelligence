import { ArrowUpRight, ArrowDownRight, FileText, Database, AlertTriangle, Sparkles, CheckCircle2, GitPullRequest, Clock } from "lucide-react";
import { Confidence } from "@/components/Confidence";

const kpis = [
  { label: "Total rules indexed", value: "12,847", delta: "+312", trend: "up", icon: FileText },
  { label: "Sources monitored", value: "184", delta: "+6", trend: "up", icon: Database },
  { label: "Recent changes (7d)", value: "47", delta: "+18", trend: "up", icon: GitPullRequest },
  { label: "Avg confidence", value: "91.4%", delta: "+1.2%", trend: "up", icon: Sparkles },
];

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
  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-[1600px]">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <p className="text-xs uppercase tracking-widest text-muted-foreground">Overview</p>
          <h1 className="text-3xl font-bold tracking-tight mt-1">Good morning, Alex</h1>
          <p className="text-sm text-muted-foreground mt-1">Here's what's happening across your rule estate today.</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Clock className="h-3.5 w-3.5" />
          <span>Last sync 2 minutes ago</span>
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
              <span className={`inline-flex items-center gap-0.5 text-[11px] font-medium px-1.5 py-0.5 rounded ${
                k.trend === "up" ? "text-success bg-success/10" : "text-destructive bg-destructive/10"
              }`}>
                {k.trend === "up" ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                {k.delta}
              </span>
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
