const retrievedRules = [
  {
    title: "Quarterly sales tax return due on last day of month following quarter end",
    source: "CDTFA — Sales and Use Tax in California",
    confidence: 82,
    status: "Published",
  },
  {
    title: "Electronic filing required for sellers with annual taxable sales over threshold",
    source: "California Code of Regulations Title 18",
    confidence: 74,
    status: "Needs review",
  },
];

const citations = [
  "Return must be filed by the last day of the month following the end of the quarter…",
  "Electronic filing is required when annual taxable sales exceed the stated threshold…",
];

export function ProductPreview() {
  return (
    <section className="border-b border-[hsl(var(--landing-border))] bg-white">
      <div className="mx-auto max-w-7xl px-6 py-16 lg:px-8 lg:py-20">
        <div className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="landing-label mb-3">Product preview</p>
            <h2 className="font-serif text-2xl tracking-tight text-[hsl(var(--landing-fg))] md:text-3xl">
              Sample workflow — not live production data
            </h2>
          </div>
          <p className="max-w-sm text-sm text-[hsl(var(--landing-muted))]">
            Illustrative UI showing query, retrieval, citations, confidence, and review routing.
          </p>
        </div>

        <div className="landing-card overflow-hidden">
          <div className="flex items-center gap-2 border-b border-[hsl(var(--landing-border))] bg-[hsl(40_20%_97%)] px-4 py-2.5">
            <div className="flex gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-[hsl(0_0%_80%)]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[hsl(0_0%_80%)]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[hsl(0_0%_80%)]" />
            </div>
            <span className="ml-3 font-mono text-[11px] text-[hsl(var(--landing-muted))]">
              lex.app/search — demo preview
            </span>
          </div>

          <div className="grid gap-0 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="border-b border-[hsl(var(--landing-border))] p-6 lg:border-b-0 lg:border-r">
              <p className="landing-label mb-3">Query</p>
              <div className="border border-[hsl(var(--landing-border))] bg-[hsl(40_20%_98%)] p-4">
                <p className="text-sm leading-relaxed text-[hsl(var(--landing-fg))]">
                  What are the sales tax filing requirements in California?
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <span className="border border-[hsl(var(--landing-border))] px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-[hsl(var(--landing-muted))]">
                    State: California
                  </span>
                  <span className="border border-[hsl(var(--landing-border))] px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-[hsl(var(--landing-muted))]">
                    Tax type: sales_tax
                  </span>
                </div>
              </div>

              <p className="landing-label mb-3 mt-6">Retrieved rules</p>
              <div className="space-y-3">
                {retrievedRules.map((rule) => (
                  <div
                    key={rule.title}
                    className="border border-[hsl(var(--landing-border))] p-4"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm font-medium leading-snug text-[hsl(var(--landing-fg))]">
                        {rule.title}
                      </p>
                      <span
                        className={`shrink-0 border px-2 py-0.5 text-[9px] uppercase tracking-[0.12em] ${
                          rule.status === "Published"
                            ? "border-[hsl(var(--landing-accent))]/30 text-[hsl(var(--landing-accent))]"
                            : "border-amber-300 text-amber-700"
                        }`}
                      >
                        {rule.status}
                      </span>
                    </div>
                    <p className="mt-2 font-mono text-[11px] text-[hsl(var(--landing-muted))]">
                      {rule.source}
                    </p>
                    <div className="mt-3 flex items-center gap-3">
                      <div className="h-px flex-1 bg-[hsl(var(--landing-border))]">
                        <div
                          className="h-px bg-[hsl(var(--landing-accent))]"
                          style={{ width: `${rule.confidence}%` }}
                        />
                      </div>
                      <span className="font-mono text-[11px] text-[hsl(var(--landing-muted))]">
                        {rule.confidence}% conf.
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-6">
              <p className="landing-label mb-3">Grounded answer</p>
              <p className="text-sm leading-relaxed text-[hsl(var(--landing-fg))]">
                California sellers generally must file quarterly sales and use tax returns by the
                last day of the month following each quarter. Electronic filing may be required
                above certain thresholds. Answers are assembled from retrieved rules with linked
                source evidence.
              </p>

              <p className="landing-label mb-3 mt-6">Source chunks</p>
              <div className="space-y-2">
                {citations.map((snippet, i) => (
                  <div
                    key={i}
                    className="border-l-2 border-[hsl(var(--landing-accent))] bg-[hsl(40_20%_98%)] px-3 py-2 text-xs leading-relaxed text-[hsl(var(--landing-muted))]"
                  >
                    {snippet}
                  </div>
                ))}
              </div>

              <div className="mt-6 grid grid-cols-2 gap-3">
                <div className="border border-[hsl(var(--landing-border))] p-3">
                  <p className="landing-label">Confidence</p>
                  <p className="mt-2 font-serif text-2xl text-[hsl(var(--landing-fg))]">0.82</p>
                </div>
                <div className="border border-[hsl(var(--landing-border))] p-3">
                  <p className="landing-label">Review status</p>
                  <p className="mt-2 text-sm text-[hsl(var(--landing-fg))]">Auto-validated + queue</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
