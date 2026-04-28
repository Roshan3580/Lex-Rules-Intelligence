import { useEffect, useMemo, useRef, useState } from "react";
import {
  Upload,
  Link2,
  FileText,
  Globe,
  CheckCircle2,
  Clock,
  AlertCircle,
  ArrowRight,
  Loader2,
  Trash2,
  Play,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  api,
  IngestRunResult,
  SourceRow,
  StateOut,
  TAX_TYPES,
  TaxType,
  taxTypeLabel,
} from "@/lib/api";

type Status = "processed" | "pending" | "error";

function statusFor(s: SourceRow): Status {
  if (s.status === "ingested") return "processed";
  if (s.status === "error") return "error";
  return "pending";
}

function timeAgo(iso: string): string {
  const t = new Date(iso).getTime();
  const diff = Date.now() - t;
  if (diff < 60_000) return "just now";
  if (diff < 3_600_000) return `${Math.round(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.round(diff / 3_600_000)}h ago`;
  return `${Math.round(diff / 86_400_000)}d ago`;
}

const Sources = () => {
  const [sources, setSources] = useState<SourceRow[]>([]);
  const [states, setStates] = useState<StateOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRun, setLastRun] = useState<IngestRunResult | null>(null);
  const [runBusy, setRunBusy] = useState(false);

  // Add-URL form
  const [url, setUrl] = useState("");
  const [urlState, setUrlState] = useState("");
  const [urlTaxType, setUrlTaxType] = useState<TaxType | "">("");
  const [urlBusy, setUrlBusy] = useState(false);

  // Upload
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploadBusy, setUploadBusy] = useState(false);
  const [uploadState, setUploadState] = useState("");
  const [uploadTaxType, setUploadTaxType] = useState<TaxType | "">("");

  async function loadSources() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listSources();
      setSources(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSources();
    api.states().then(setStates).catch(() => setStates([]));
  }, []);

  const totals = useMemo(() => {
    const t = { processed: 0, pending: 0, error: 0, rules: 0 };
    for (const s of sources) {
      const st = statusFor(s);
      t[st] += 1;
      t.rules += s.rule_count;
    }
    return t;
  }, [sources]);

  async function onAddUrl(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setUrlBusy(true);
    setError(null);
    try {
      await api.ingestSource({
        source_type: "webpage",
        url: url.trim(),
        state: urlState || undefined,
        tax_type: (urlTaxType || undefined) as TaxType | undefined,
      });
      setUrl("");
      await loadSources();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setUrlBusy(false);
    }
  }

  async function onUploadFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setUploadBusy(true);
    setError(null);
    try {
      for (const file of Array.from(files)) {
        await api.uploadFile(file, {
          state: uploadState || undefined,
          tax_type: (uploadTaxType || undefined) as TaxType | undefined,
        });
      }
      await loadSources();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setUploadBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function onRunIngestion() {
    if (
      !confirm(
        "Run ingestion against the curated sources.yaml list? This will fetch each URL and may take a minute.",
      )
    )
      return;
    setRunBusy(true);
    setError(null);
    setLastRun(null);
    try {
      const r = await api.ingestRun();
      setLastRun(r);
      await loadSources();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunBusy(false);
    }
  }

  async function onDelete(id: string) {
    if (!confirm("Delete this source and all its chunks?")) return;
    await api.deleteSource(id);
    await loadSources();
  }

  const stages = [
    { name: "Connected", count: sources.length, color: "primary" },
    { name: "Processed", count: totals.processed, color: "teal" },
    { name: "Pending", count: totals.pending, color: "warning" },
    { name: "Indexed rules", count: totals.rules, color: "success" },
  ];

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-[1600px]">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <p className="text-xs uppercase tracking-widest text-muted-foreground">
            Data layer
          </p>
          <h1 className="text-3xl font-bold tracking-tight mt-1">Sources</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Connect state tax department websites, PDFs, and manual text to
            your rule index.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadSources}
            disabled={loading}
          >
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            Refresh
          </Button>
          <Button
            variant="hero"
            size="sm"
            onClick={onRunIngestion}
            disabled={runBusy}
          >
            {runBusy ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Play className="h-3.5 w-3.5" />
            )}
            Run ingestion
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-sm flex items-start gap-3">
          <AlertCircle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
          <div>
            <p className="font-medium text-destructive">Request failed</p>
            <p className="text-xs text-muted-foreground mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Pipeline */}
      <div className="rounded-2xl glass p-6">
        <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-4">
          Live pipeline
        </p>
        <div className="flex items-center gap-2 overflow-x-auto">
          {stages.map((s, i) => (
            <div key={s.name} className="flex items-center gap-2 shrink-0">
              <div className="rounded-xl border border-border bg-secondary/40 px-4 py-3 min-w-[140px]">
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                  {s.name}
                </p>
                <p className="text-2xl font-bold mt-1">{s.count}</p>
                <div className={`mt-2 h-0.5 rounded-full bg-${s.color}`} />
              </div>
              {i < stages.length - 1 && (
                <ArrowRight className="h-4 w-4 text-muted-foreground/50" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Last run summary */}
      {lastRun && (
        <div className="rounded-2xl glass p-5 text-sm">
          <p className="font-semibold mb-1">Last ingestion run</p>
          <p className="text-muted-foreground text-xs mb-3">
            {lastRun.ingested} ingested · {lastRun.duplicates} duplicates ·{" "}
            {lastRun.errors} errors · {lastRun.total} total
          </p>
          <div className="grid md:grid-cols-2 gap-2 max-h-64 overflow-y-auto">
            {lastRun.items.map((it, i) => (
              <div
                key={i}
                className="text-xs px-3 py-2 rounded-lg border border-border/60 bg-secondary/30"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium truncate">{it.name}</span>
                  <span
                    className={`text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded ${
                      it.status === "ingested"
                        ? "bg-success/10 text-success"
                        : it.status === "duplicate"
                          ? "bg-secondary text-muted-foreground"
                          : "bg-destructive/10 text-destructive"
                    }`}
                  >
                    {it.status}
                  </span>
                </div>
                <p className="text-muted-foreground mt-0.5 truncate">
                  {it.error
                    ? it.error
                    : `${it.state || "—"} · ${taxTypeLabel(it.tax_type)} · ${it.chunks_created} chunks · ${it.rules_created} rules`}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload + URL */}
      <div className="grid md:grid-cols-2 gap-4">
        <div className="rounded-2xl glass p-6 border-dashed border-2 border-border hover:border-primary/40 transition-colors">
          <div className="flex flex-col items-center text-center py-2">
            <div className="h-12 w-12 rounded-xl bg-gradient-primary/20 border border-primary/30 flex items-center justify-center mb-4">
              <Upload className="h-5 w-5 text-primary" />
            </div>
            <p className="text-sm font-semibold">Drop PDFs to ingest</p>
            <p className="text-xs text-muted-foreground mt-1">
              PDF, TXT, MD, or HTML · auto-extracts rules
            </p>
            <div className="grid grid-cols-2 gap-2 w-full mt-4">
              <select
                className="h-9 px-2 rounded-lg bg-secondary border border-border text-xs focus:outline-none focus:border-primary/40"
                value={uploadState}
                onChange={(e) => setUploadState(e.target.value)}
              >
                <option value="">State (optional)</option>
                {states.map((s) => (
                  <option key={s.abbreviation} value={s.name}>
                    {s.name}
                  </option>
                ))}
              </select>
              <select
                className="h-9 px-2 rounded-lg bg-secondary border border-border text-xs focus:outline-none focus:border-primary/40"
                value={uploadTaxType}
                onChange={(e) => setUploadTaxType(e.target.value as TaxType | "")}
              >
                <option value="">Tax type (optional)</option>
                {TAX_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.txt,.md,.html,.htm"
              multiple
              className="hidden"
              onChange={(e) => onUploadFiles(e.target.files)}
            />
            <Button
              variant="outline"
              size="sm"
              className="mt-3"
              disabled={uploadBusy}
              onClick={() => fileRef.current?.click()}
            >
              {uploadBusy ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Upload className="h-3.5 w-3.5" />
              )}
              Choose files
            </Button>
          </div>
        </div>

        <form onSubmit={onAddUrl} className="rounded-2xl glass p-6">
          <div className="flex items-center gap-2 mb-4">
            <Link2 className="h-4 w-4 text-primary" />
            <p className="text-sm font-semibold">Add a state tax website</p>
          </div>
          <div className="space-y-3">
            <input
              placeholder="https://www.cdtfa.ca.gov/taxes-and-fees/sutprograms.htm"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="w-full h-10 px-3 rounded-lg bg-secondary border border-border text-sm focus:outline-none focus:border-primary/40"
            />
            <div className="grid grid-cols-2 gap-2">
              <select
                className="h-10 px-3 rounded-lg bg-secondary border border-border text-sm focus:outline-none"
                value={urlState}
                onChange={(e) => setUrlState(e.target.value)}
              >
                <option value="">State (optional)</option>
                {states.map((s) => (
                  <option key={s.abbreviation} value={s.name}>
                    {s.name}
                  </option>
                ))}
              </select>
              <select
                className="h-10 px-3 rounded-lg bg-secondary border border-border text-sm focus:outline-none"
                value={urlTaxType}
                onChange={(e) => setUrlTaxType(e.target.value as TaxType | "")}
              >
                <option value="">Tax type (optional)</option>
                {TAX_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
            <Button
              type="submit"
              variant="hero"
              size="default"
              className="w-full"
              disabled={urlBusy || !url.trim()}
            >
              {urlBusy ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : null}
              Connect source
            </Button>
          </div>
        </form>
      </div>

      {/* Sources list */}
      <div className="rounded-2xl glass overflow-hidden">
        <div className="p-5 border-b border-border flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold">All sources</h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              {sources.length} connected · {totals.rules.toLocaleString()} rules
              extracted
            </p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-[11px] uppercase tracking-wider text-muted-foreground bg-secondary/30">
              <tr>
                <th className="text-left font-semibold px-5 py-3">Source</th>
                <th className="text-left font-semibold px-5 py-3">Type</th>
                <th className="text-left font-semibold px-5 py-3">Status</th>
                <th className="text-left font-semibold px-5 py-3">State</th>
                <th className="text-left font-semibold px-5 py-3">Tax type</th>
                <th className="text-right font-semibold px-5 py-3">Chunks</th>
                <th className="text-right font-semibold px-5 py-3">Rules</th>
                <th className="text-left font-semibold px-5 py-3">Updated</th>
                <th className="px-5 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {sources.map((s) => {
                const st = statusFor(s);
                return (
                  <tr
                    key={s.id}
                    className="border-t border-border/40 hover:bg-secondary/20 transition-colors"
                  >
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-2.5">
                        {s.source_type === "pdf" && (
                          <FileText className="h-4 w-4 text-primary" />
                        )}
                        {(s.source_type === "url" ||
                          s.source_type === "webpage") && (
                          <Globe className="h-4 w-4 text-teal" />
                        )}
                        {s.source_type !== "pdf" &&
                          s.source_type !== "url" &&
                          s.source_type !== "webpage" && (
                            <Link2 className="h-4 w-4 text-accent" />
                          )}
                        <div className="min-w-0">
                          <span className="font-medium block truncate max-w-[280px]">
                            {s.name}
                          </span>
                          {s.url && (
                            <a
                              href={s.url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-[11px] text-muted-foreground hover:text-primary truncate block max-w-[280px]"
                            >
                              {s.url}
                            </a>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3.5 text-xs text-muted-foreground font-mono">
                      {s.source_type}
                    </td>
                    <td className="px-5 py-3.5">
                      <span
                        className={`inline-flex items-center gap-1.5 text-[11px] font-medium px-2 py-0.5 rounded ${
                          st === "processed"
                            ? "bg-success/10 text-success"
                            : st === "pending"
                              ? "bg-warning/10 text-warning"
                              : "bg-destructive/10 text-destructive"
                        }`}
                      >
                        {st === "processed" && <CheckCircle2 className="h-3 w-3" />}
                        {st === "pending" && <Clock className="h-3 w-3" />}
                        {st === "error" && <AlertCircle className="h-3 w-3" />}
                        {s.status}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="text-[11px] px-1.5 py-0.5 rounded bg-secondary border border-border text-muted-foreground">
                        {s.state || "—"}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-xs text-muted-foreground">
                      {taxTypeLabel(s.tax_category)}
                    </td>
                    <td className="px-5 py-3.5 text-right font-mono text-sm">
                      {s.chunk_count.toLocaleString()}
                    </td>
                    <td className="px-5 py-3.5 text-right font-mono text-sm">
                      {s.rule_count.toLocaleString()}
                    </td>
                    <td className="px-5 py-3.5 text-xs text-muted-foreground">
                      {timeAgo(s.updated_at)}
                    </td>
                    <td className="px-5 py-3.5">
                      <button
                        className="text-muted-foreground hover:text-destructive"
                        onClick={() => onDelete(s.id)}
                        title="Delete source"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                );
              })}
              {sources.length === 0 && !loading && (
                <tr>
                  <td
                    colSpan={9}
                    className="px-5 py-10 text-center text-muted-foreground text-sm"
                  >
                    No sources yet. Click <strong>Run ingestion</strong> to load
                    the curated state tax sources, or upload a PDF / paste a URL
                    above.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Sources;
