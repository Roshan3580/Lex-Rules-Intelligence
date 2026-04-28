import { Upload, Link2, FileText, Globe, CheckCircle2, Clock, AlertCircle, MoreHorizontal, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

const sources = [
  { name: "PSD2 Directive 2015/2366", type: "PDF", status: "processed", updated: "2h ago", rules: 247, jurisdiction: "EU" },
  { name: "fatf-gafi.org/recommendations", type: "URL", status: "processed", updated: "1d ago", rules: 89, jurisdiction: "Global" },
  { name: "BaFin Circular 09/2026", type: "PDF", status: "pending", updated: "12m ago", rules: 0, jurisdiction: "DE" },
  { name: "OFAC SDN List API", type: "API", status: "processed", updated: "5m ago", rules: 1247, jurisdiction: "US" },
  { name: "EBA Guidelines 2022/03", type: "PDF", status: "processed", updated: "3d ago", rules: 56, jurisdiction: "EU" },
  { name: "bafin.de/regulations", type: "URL", status: "error", updated: "6h ago", rules: 0, jurisdiction: "DE" },
];

const stages = [
  { name: "Ingestion", count: 184, color: "primary" },
  { name: "Extraction", count: 12, color: "teal" },
  { name: "Validation", count: 4, color: "warning" },
  { name: "Published", count: 168, color: "success" },
];

const Sources = () => {
  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-[1600px]">
      <div>
        <p className="text-xs uppercase tracking-widest text-muted-foreground">Data layer</p>
        <h1 className="text-3xl font-bold tracking-tight mt-1">Sources</h1>
        <p className="text-sm text-muted-foreground mt-1">Connect documents, websites, and APIs to your rule index.</p>
      </div>

      {/* Pipeline */}
      <div className="rounded-2xl glass p-6">
        <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-4">Live pipeline</p>
        <div className="flex items-center gap-2 overflow-x-auto">
          {stages.map((s, i) => (
            <div key={s.name} className="flex items-center gap-2 shrink-0">
              <div className="rounded-xl border border-border bg-secondary/40 px-4 py-3 min-w-[140px]">
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{s.name}</p>
                <p className="text-2xl font-bold mt-1">{s.count}</p>
                <div className={`mt-2 h-0.5 rounded-full bg-${s.color}`} />
              </div>
              {i < stages.length - 1 && <ArrowRight className="h-4 w-4 text-muted-foreground/50" />}
            </div>
          ))}
        </div>
      </div>

      {/* Upload */}
      <div className="grid md:grid-cols-2 gap-4">
        <div className="rounded-2xl glass p-6 border-dashed border-2 border-border hover:border-primary/40 transition-colors cursor-pointer group">
          <div className="flex flex-col items-center text-center py-6">
            <div className="h-12 w-12 rounded-xl bg-gradient-primary/20 border border-primary/30 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <Upload className="h-5 w-5 text-primary" />
            </div>
            <p className="text-sm font-semibold">Drop PDFs to ingest</p>
            <p className="text-xs text-muted-foreground mt-1">or click to browse · max 100MB</p>
            <Button variant="outline" size="sm" className="mt-4">Choose files</Button>
          </div>
        </div>

        <div className="rounded-2xl glass p-6">
          <div className="flex items-center gap-2 mb-4">
            <Link2 className="h-4 w-4 text-primary" />
            <p className="text-sm font-semibold">Add URL or API endpoint</p>
          </div>
          <div className="space-y-3">
            <input
              placeholder="https://regulator.gov/rules"
              className="w-full h-10 px-3 rounded-lg bg-secondary border border-border text-sm focus:outline-none focus:border-primary/40"
            />
            <div className="flex gap-2">
              <select className="h-10 px-3 rounded-lg bg-secondary border border-border text-sm focus:outline-none">
                <option>Auto-detect</option>
                <option>Web page</option>
                <option>REST API</option>
                <option>RSS feed</option>
              </select>
              <Button variant="hero" size="default" className="flex-1">Connect source</Button>
            </div>
          </div>
        </div>
      </div>

      {/* Sources list */}
      <div className="rounded-2xl glass overflow-hidden">
        <div className="p-5 border-b border-border flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold">All sources</h2>
            <p className="text-xs text-muted-foreground mt-0.5">{sources.length} connected · 1,639 rules indexed</p>
          </div>
          <Button variant="outline" size="sm">Export</Button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-[11px] uppercase tracking-wider text-muted-foreground bg-secondary/30">
              <tr>
                <th className="text-left font-semibold px-5 py-3">Source</th>
                <th className="text-left font-semibold px-5 py-3">Type</th>
                <th className="text-left font-semibold px-5 py-3">Status</th>
                <th className="text-left font-semibold px-5 py-3">Jurisdiction</th>
                <th className="text-right font-semibold px-5 py-3">Rules</th>
                <th className="text-left font-semibold px-5 py-3">Last updated</th>
                <th className="px-5 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {sources.map((s) => (
                <tr key={s.name} className="border-t border-border/40 hover:bg-secondary/20 transition-colors">
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-2.5">
                      {s.type === "PDF" && <FileText className="h-4 w-4 text-primary" />}
                      {s.type === "URL" && <Globe className="h-4 w-4 text-teal" />}
                      {s.type === "API" && <Link2 className="h-4 w-4 text-accent" />}
                      <span className="font-medium">{s.name}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3.5 text-xs text-muted-foreground font-mono">{s.type}</td>
                  <td className="px-5 py-3.5">
                    <span className={`inline-flex items-center gap-1.5 text-[11px] font-medium px-2 py-0.5 rounded ${
                      s.status === "processed" ? "bg-success/10 text-success" :
                      s.status === "pending" ? "bg-warning/10 text-warning" :
                      "bg-destructive/10 text-destructive"
                    }`}>
                      {s.status === "processed" && <CheckCircle2 className="h-3 w-3" />}
                      {s.status === "pending" && <Clock className="h-3 w-3" />}
                      {s.status === "error" && <AlertCircle className="h-3 w-3" />}
                      {s.status}
                    </span>
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="text-[11px] px-1.5 py-0.5 rounded bg-secondary border border-border text-muted-foreground">
                      {s.jurisdiction}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-right font-mono text-sm">{s.rules.toLocaleString()}</td>
                  <td className="px-5 py-3.5 text-xs text-muted-foreground">{s.updated}</td>
                  <td className="px-5 py-3.5">
                    <button className="text-muted-foreground hover:text-foreground">
                      <MoreHorizontal className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Sources;
