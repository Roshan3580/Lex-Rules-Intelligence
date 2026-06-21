import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Sparkles,
  ArrowRight,
  ExternalLink,
  FileText,
  Filter,
  BookOpen,
  Loader2,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";
import { Confidence } from "@/components/Confidence";
import { AppSectionHeader } from "@/components/app/AppSectionHeader";
import { Button } from "@/components/ui/button";
import {
  api,
  confidenceToPct,
  Rule,
  QueryResponse,
  StateOut,
  TAX_TYPES,
  TaxType,
  taxTypeLabel,
} from "@/lib/api";

const SAMPLE_QUESTIONS = [
  {
    q: "What are the sales tax filing requirements in California?",
    state: "California",
    tax_type: "sales_tax" as TaxType,
  },
  {
    q: "What payroll tax rules apply in Texas?",
    state: "Texas",
    tax_type: "payroll_tax" as TaxType,
  },
  {
    q: "What forms are required for New York employer withholding?",
    state: "New York",
    tax_type: "withholding" as TaxType,
  },
  {
    q: "What are the filing deadlines for Florida corporate tax?",
    state: "Florida",
    tax_type: "corporate_tax" as TaxType,
  },
];

const RuleSearch = () => {
  const [states, setStates] = useState<StateOut[]>([]);
  const [query, setQuery] = useState(
    "What are the sales tax filing requirements in California?",
  );
  const [state, setState] = useState<string>("California");
  const [taxType, setTaxType] = useState<TaxType | "">("sales_tax");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [selected, setSelected] = useState<number>(0);
  const [elapsedMs, setElapsedMs] = useState<number | null>(null);

  useEffect(() => {
    api.states().then(setStates).catch(() => setStates([]));
  }, []);

  const rules = result?.rules_used ?? [];
  const sources = result?.sources ?? [];

  async function runQuery(override?: {
    q?: string;
    state?: string;
    tax_type?: TaxType | "";
  }) {
    const q = (override?.q ?? query).trim();
    if (!q) return;
    if (override?.q !== undefined) setQuery(override.q);
    if (override?.state !== undefined) setState(override.state);
    if (override?.tax_type !== undefined) setTaxType(override.tax_type);

    setLoading(true);
    setError(null);
    setResult(null);
    setSelected(0);
    const t0 = performance.now();
    try {
      const data = await api.query({
        question: q,
        state: (override?.state ?? state) || undefined,
        tax_type:
          ((override?.tax_type ?? taxType) || undefined) as TaxType | undefined,
      });
      setResult(data);
      setElapsedMs(Math.round(performance.now() - t0));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    runQuery();
  }

  const selectedRule: Rule | undefined = rules[selected];
  const selectedSource = sources[selected] ?? sources[0];

  const activeFilters = useMemo(
    () =>
      [
        state ? { label: "State", value: state, kind: "state" as const } : null,
        taxType
          ? { label: "Tax type", value: taxTypeLabel(taxType), kind: "tax_type" as const }
          : null,
      ].filter(Boolean) as { label: string; value: string; kind: "state" | "tax_type" }[],
    [state, taxType],
  );

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* Main */}
      <div className="flex-1 overflow-y-auto p-6 lg:p-8 max-w-[1100px]">
        <AppSectionHeader
          className="mb-6"
          label="Rule intelligence"
          title="Rule search"
          description="Ask a state tax question. Answers are grounded in indexed sources with citations and a confidence score."
        />

        {/* Query */}
        <form onSubmit={handleSubmit}>
          <div className="relative border border-border bg-card">
            <div className="flex items-start gap-3 p-5">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center border border-primary/20 bg-primary/5">
                <Sparkles className="h-4 w-4 text-primary" />
              </div>
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                rows={2}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                    e.preventDefault();
                    runQuery();
                  }
                }}
                className="flex-1 bg-transparent resize-none text-base placeholder:text-muted-foreground focus:outline-none"
                placeholder="Ask: What rules apply for X tax in Y state?"
              />
              <Button
                type="submit"
                variant="hero"
                size="sm"
                disabled={loading || !query.trim()}
              >
                {loading ? (
                  <>
                    Searching <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  </>
                ) : (
                  <>
                    Search <ArrowRight className="h-3.5 w-3.5" />
                  </>
                )}
              </Button>
            </div>

            <div className="px-5 pb-4 flex items-center gap-2 flex-wrap border-t border-border/40 pt-3">
              <Filter className="h-3.5 w-3.5 text-muted-foreground" />

              <label className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-md bg-secondary border border-border/60">
                <span className="text-muted-foreground">State:</span>
                <select
                  className="bg-transparent text-foreground font-medium focus:outline-none"
                  value={state}
                  onChange={(e) => setState(e.target.value)}
                >
                  <option value="">Any</option>
                  {states.map((s) => (
                    <option key={s.abbreviation} value={s.name}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-md bg-secondary border border-border/60">
                <span className="text-muted-foreground">Tax type:</span>
                <select
                  className="bg-transparent text-foreground font-medium focus:outline-none"
                  value={taxType}
                  onChange={(e) => setTaxType(e.target.value as TaxType | "")}
                >
                  <option value="">Any</option>
                  {TAX_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </label>

              {activeFilters.length > 0 && (
                <span className="text-[11px] text-muted-foreground ml-auto">
                  {activeFilters.length} filter
                  {activeFilters.length === 1 ? "" : "s"} applied
                </span>
              )}
            </div>
          </div>
        </form>

        {/* Sample questions */}
        {!result && !loading && !error && (
          <div className="mt-6 flex flex-wrap gap-2">
            <span className="text-xs text-muted-foreground pt-1">Try:</span>
            {SAMPLE_QUESTIONS.map((s) => (
              <button
                key={s.q}
                type="button"
                onClick={() => runQuery({ q: s.q, state: s.state, tax_type: s.tax_type })}
                className="text-xs rounded-full border border-border/60 bg-secondary/50 px-3 py-1.5 hover:bg-secondary transition-colors"
              >
                {s.q}
              </button>
            ))}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mt-6 rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-sm flex items-start gap-3">
            <AlertTriangle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
            <div className="flex-1">
              <p className="font-medium text-destructive">Query failed</p>
              <p className="text-xs text-muted-foreground mt-0.5">{error}</p>
              <p className="text-xs text-muted-foreground mt-1">
                Make sure the backend is running on port 8000 (uvicorn
                app.main:app --port 8000).
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={() => runQuery()}>
              <RefreshCw className="h-3 w-3" /> Retry
            </Button>
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div className="mt-8 space-y-3">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="rounded-2xl border border-border/60 bg-card/40 p-5 animate-pulse"
              >
                <div className="h-4 w-3/4 bg-secondary rounded mb-3" />
                <div className="h-3 w-full bg-secondary/70 rounded mb-2" />
                <div className="h-3 w-5/6 bg-secondary/50 rounded" />
              </div>
            ))}
          </div>
        )}

        {/* Answer + Results */}
        {result && !loading && (
          <div className="mt-8 space-y-6">
            {/* Answer summary */}
            <section className="rounded-2xl border border-primary/30 bg-gradient-to-br from-primary/5 to-transparent p-5">
              <div className="flex items-start justify-between gap-3 mb-3">
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-primary font-semibold">
                    Grounded answer
                    {result.state && ` · ${result.state}`}
                    {result.tax_type && ` · ${taxTypeLabel(result.tax_type)}`}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {result.method === "llm"
                      ? "Generated by the configured LLM, grounded on retrieved sources."
                      : "Deterministic fallback summary (no LLM key configured)."}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Confidence value={confidenceToPct(result.confidence)} />
                  <span
                    className={`text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded ${
                      result.method === "llm"
                        ? "bg-success/10 text-success"
                        : "bg-warning/10 text-warning"
                    }`}
                  >
                    {result.method === "llm" ? "LLM" : "fallback"}
                  </span>
                </div>
              </div>
              <p className="text-sm leading-relaxed text-foreground/90 whitespace-pre-wrap">
                {result.answer}
              </p>
            </section>

            {/* Rules header */}
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                <span className="text-foreground font-medium">
                  {rules.length} rule{rules.length === 1 ? "" : "s"}
                </span>{" "}
                used · {sources.length} source citation
                {sources.length === 1 ? "" : "s"}
              </p>
              {elapsedMs !== null && (
                <div className="text-[11px] text-muted-foreground font-mono">
                  processed in {elapsedMs}ms
                </div>
              )}
            </div>

            {/* Rules list */}
            {rules.length === 0 && sources.length === 0 ? (
              <div className="rounded-2xl border border-warning/30 bg-warning/5 p-5 text-sm">
                <p className="font-medium text-warning">
                  No grounded sources found for this filter combination.
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Try removing the state or tax type filter, or upload a
                  relevant source on the Sources page.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {rules.map((r, i) => (
                  <button
                    key={r.id}
                    onClick={() => setSelected(i)}
                    className={`w-full text-left rounded-2xl border p-5 transition-all ${
                      selected === i
                        ? "border-primary/50 bg-card shadow-elegant"
                        : "border-border/60 bg-card/40 hover:border-border hover:bg-card/70"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4 mb-3">
                      <h3 className="text-base font-semibold leading-snug">
                        {r.rule_title}
                      </h3>
                      <Confidence value={confidenceToPct(r.confidence_score)} />
                    </div>
                    <p className="text-sm text-muted-foreground leading-relaxed mb-4">
                      {r.rule_summary}
                    </p>

                    <div className="grid md:grid-cols-2 gap-3 mb-4">
                      <ChipColumn
                        label="Required actions"
                        items={r.required_actions}
                        dotClass="bg-primary"
                      />
                      <ChipColumn
                        label="Required forms / deadlines"
                        items={[
                          ...(r.required_forms || []),
                          ...(r.deadlines || []),
                        ]}
                        dotClass="bg-teal"
                      />
                    </div>

                    {r.exceptions && r.exceptions.length > 0 && (
                      <div className="mb-4">
                        <ChipColumn
                          label="Exceptions"
                          items={r.exceptions}
                          dotClass="bg-warning"
                        />
                      </div>
                    )}

                    <div className="flex items-center justify-between pt-3 border-t border-border/40">
                      <div className="flex items-center gap-2 text-xs min-w-0">
                        <BookOpen className="h-3 w-3 text-muted-foreground shrink-0" />
                        <span className="text-muted-foreground font-mono truncate">
                          {r.source_document_name || r.source_url || "internal"}
                        </span>
                        {r.source_url && (
                          <ExternalLink className="h-3 w-3 text-muted-foreground shrink-0" />
                        )}
                      </div>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-secondary border border-border text-muted-foreground">
                        {r.state} · {taxTypeLabel(r.tax_category)}
                      </span>
                    </div>
                  </button>
                ))}

                {/* Sources without an associated rule */}
                {rules.length === 0 && sources.length > 0 && (
                  <div className="space-y-3">
                    {sources.map((s, i) => (
                      <button
                        key={i}
                        onClick={() => setSelected(i)}
                        className="w-full text-left rounded-2xl border border-border/60 bg-card/40 p-5 hover:border-border hover:bg-card/70"
                      >
                        <div className="flex items-start justify-between gap-3 mb-2">
                          <h3 className="text-base font-semibold leading-snug">
                            {s.title}
                          </h3>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-secondary border border-border text-muted-foreground">
                            {s.document_type}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground leading-relaxed">
                          {s.snippet}
                        </p>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Side panel */}
      {result && !loading && (rules.length > 0 || sources.length > 0) && (
        <aside className="hidden xl:flex w-[420px] shrink-0 flex-col overflow-y-auto border-l border-border bg-card">
          <div className="p-6 border-b border-border">
            <p className="text-[10px] uppercase tracking-widest text-primary mb-1 flex items-center gap-1">
              <Sparkles className="h-3 w-3" /> Why this answer?
            </p>
            <h3 className="text-sm font-semibold leading-snug">
              {selectedRule?.rule_title || selectedSource?.title || "Sources"}
            </h3>
          </div>
          <div className="p-6 space-y-5">
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2 font-semibold">
                Reasoning
              </p>
              <p className="text-sm text-foreground/90 leading-relaxed">
                Filtered by{" "}
                <span className="text-primary font-medium">
                  {result.state || "any state"}
                </span>{" "}
                and{" "}
                <span className="text-primary font-medium">
                  {taxTypeLabel(result.tax_type)}
                </span>
                . Retrieved {rules.length} rule
                {rules.length === 1 ? "" : "s"} and{" "}
                {sources.length} source snippet
                {sources.length === 1 ? "" : "s"}, ranked by relevance.
              </p>
            </div>

            {selectedRule?.source_snippet && (
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2 font-semibold">
                  Source preview
                </p>
                <div className="rounded-xl border border-border bg-card/60 p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <FileText className="h-4 w-4 text-primary" />
                    <p className="text-xs font-mono text-muted-foreground truncate">
                      {selectedRule.source_document_name ||
                        selectedRule.source_url ||
                        "internal"}
                    </p>
                  </div>
                  <p className="text-xs text-foreground/80 leading-relaxed italic">
                    "{selectedRule.source_snippet}"
                  </p>
                  {selectedRule.source_url && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-3 w-full"
                      asChild
                    >
                      <a
                        href={selectedRule.source_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open full source <ExternalLink className="h-3 w-3" />
                      </a>
                    </Button>
                  )}
                </div>
              </div>
            )}

            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2 font-semibold">
                Citations ({sources.length})
              </p>
              <div className="space-y-2">
                {sources.map((s, i) => (
                  <a
                    key={i}
                    href={s.url || "#"}
                    target={s.url ? "_blank" : undefined}
                    rel={s.url ? "noreferrer" : undefined}
                    onClick={(e) => {
                      if (!s.url) e.preventDefault();
                    }}
                    className="block text-xs px-3 py-2 rounded-lg bg-secondary/60 hover:bg-secondary cursor-pointer transition-colors"
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="font-medium truncate">{s.title}</span>
                      <span className="text-[9px] uppercase tracking-wider text-muted-foreground shrink-0">
                        {s.document_type}
                      </span>
                    </div>
                    <p className="text-[11px] text-muted-foreground leading-snug line-clamp-2">
                      {s.snippet}
                    </p>
                    {s.last_checked && (
                      <p className="text-[10px] text-muted-foreground/80 mt-1 font-mono">
                        last checked {new Date(s.last_checked).toLocaleDateString()}
                      </p>
                    )}
                  </a>
                ))}
              </div>
            </div>
          </div>
        </aside>
      )}
    </div>
  );
};

function ChipColumn({
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
      <ul className="space-y-1">
        {items.slice(0, 6).map((c, i) => (
          <li
            key={`${c}-${i}`}
            className="text-xs text-foreground flex items-start gap-1.5"
          >
            <span
              className={`mt-1 h-1 w-1 rounded-full shrink-0 ${dotClass}`}
            />
            {c}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default RuleSearch;
