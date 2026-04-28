import { useState } from "react";
import { Sparkles, ArrowRight, ExternalLink, FileText, X, Filter, BookOpen } from "lucide-react";
import { Confidence } from "@/components/Confidence";
import { Button } from "@/components/ui/button";

const results = [
  {
    title: "Strong Customer Authentication required for transactions ≥ €30",
    summary: "Payment service providers must apply SCA when a payer initiates an electronic payment transaction within the EU above the threshold.",
    conditions: ["Transaction is electronic", "Amount ≥ €30", "Payer in EEA"],
    actions: ["Trigger 2FA challenge", "Log authentication evidence", "Retain proof for 5 years"],
    confidence: 96,
    source: "PSD2 Directive 2015/2366 — Article 97",
    snippet: "...payment service providers shall apply strong customer authentication where the payer accesses its payment account online, initiates an electronic payment transaction, or carries out any action through a remote channel...",
    jurisdiction: "EU",
  },
  {
    title: "Beneficial ownership disclosure for legal persons",
    summary: "Companies must obtain and hold adequate, accurate, and current information on their beneficial ownership.",
    conditions: ["Entity is a legal person", "Operates in FATF jurisdiction"],
    actions: ["Identify beneficial owners ≥ 25%", "Verify identity", "Update register annually"],
    confidence: 88,
    source: "FATF Recommendation 24",
    snippet: "Countries should ensure that there is adequate, accurate and timely information on the beneficial ownership and control of legal persons that can be obtained or accessed in a timely fashion by competent authorities...",
    jurisdiction: "Global",
  },
  {
    title: "Enhanced due diligence for high-risk third countries",
    summary: "Obliged entities must apply enhanced due diligence measures when dealing with natural persons or legal entities established in high-risk third countries.",
    conditions: ["Counterparty in high-risk country list", "Transaction value > €10,000"],
    actions: ["Obtain senior management approval", "Establish source of funds", "Enhanced ongoing monitoring"],
    confidence: 73,
    source: "EU AML Directive 2015/849 — Article 18",
    snippet: "Member States shall require obliged entities to apply enhanced customer due diligence measures in business relationships and transactions involving high-risk third countries...",
    jurisdiction: "EU",
  },
];

const filters = [
  { label: "Jurisdiction", value: "EU" },
  { label: "Workflow", value: "Onboarding" },
  { label: "Source type", value: "Regulation" },
];

const RuleSearch = () => {
  const [query, setQuery] = useState("What rules apply for cross-border B2B payments above $10K in the EU?");
  const [selected, setSelected] = useState<number | null>(0);

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* Main */}
      <div className="flex-1 overflow-y-auto p-6 lg:p-8 max-w-[1100px]">
        <div className="mb-6">
          <p className="text-xs uppercase tracking-widest text-primary mb-2 flex items-center gap-1.5">
            <Sparkles className="h-3 w-3" /> Lex copilot
          </p>
          <h1 className="text-3xl font-bold tracking-tight">Rule search</h1>
        </div>

        {/* AI Input */}
        <div className="relative rounded-2xl gradient-border shadow-elegant">
          <div className="flex items-start gap-3 p-5">
            <div className="h-9 w-9 rounded-xl bg-gradient-primary flex items-center justify-center shrink-0 shadow-glow">
              <Sparkles className="h-4 w-4 text-primary-foreground" />
            </div>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={2}
              className="flex-1 bg-transparent resize-none text-base placeholder:text-muted-foreground focus:outline-none"
              placeholder="Ask: What rules apply for X in Y jurisdiction?"
            />
            <Button variant="hero" size="sm">
              Search <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </div>
          <div className="px-5 pb-4 flex items-center gap-2 flex-wrap border-t border-border/40 pt-3">
            <Filter className="h-3.5 w-3.5 text-muted-foreground" />
            {filters.map((f) => (
              <span key={f.label} className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-md bg-secondary border border-border/60">
                <span className="text-muted-foreground">{f.label}:</span>
                <span className="font-medium">{f.value}</span>
                <X className="h-3 w-3 text-muted-foreground hover:text-foreground cursor-pointer" />
              </span>
            ))}
            <button className="text-[11px] text-primary hover:underline ml-1">+ Add filter</button>
          </div>
        </div>

        {/* Results */}
        <div className="mt-8">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-muted-foreground">
              <span className="text-foreground font-medium">3 rules</span> applied · ranked by relevance
            </p>
            <div className="text-[11px] text-muted-foreground font-mono">processed in 412ms</div>
          </div>

          <div className="space-y-3">
            {results.map((r, i) => (
              <button
                key={i}
                onClick={() => setSelected(i)}
                className={`w-full text-left rounded-2xl border p-5 transition-all ${
                  selected === i
                    ? "border-primary/50 bg-card shadow-elegant"
                    : "border-border/60 bg-card/40 hover:border-border hover:bg-card/70"
                }`}
              >
                <div className="flex items-start justify-between gap-4 mb-3">
                  <h3 className="text-base font-semibold leading-snug">{r.title}</h3>
                  <Confidence value={r.confidence} />
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed mb-4">{r.summary}</p>

                <div className="grid md:grid-cols-2 gap-3 mb-4">
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5 font-semibold">Conditions</p>
                    <ul className="space-y-1">
                      {r.conditions.map((c) => (
                        <li key={c} className="text-xs text-foreground flex items-start gap-1.5">
                          <span className="mt-1 h-1 w-1 rounded-full bg-teal shrink-0" />
                          {c}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5 font-semibold">Required actions</p>
                    <ul className="space-y-1">
                      {r.actions.map((a) => (
                        <li key={a} className="text-xs text-foreground flex items-start gap-1.5">
                          <span className="mt-1 h-1 w-1 rounded-full bg-primary shrink-0" />
                          {a}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-border/40">
                  <div className="flex items-center gap-2 text-xs">
                    <BookOpen className="h-3 w-3 text-muted-foreground" />
                    <span className="text-muted-foreground font-mono">{r.source}</span>
                    <ExternalLink className="h-3 w-3 text-muted-foreground" />
                  </div>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-secondary border border-border text-muted-foreground">
                    {r.jurisdiction}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Side panel */}
      {selected !== null && (
        <aside className="hidden xl:flex w-[420px] shrink-0 border-l border-border bg-sidebar/40 flex-col overflow-y-auto">
          <div className="p-6 border-b border-border">
            <p className="text-[10px] uppercase tracking-widest text-primary mb-1 flex items-center gap-1">
              <Sparkles className="h-3 w-3" /> Why this answer?
            </p>
            <h3 className="text-sm font-semibold leading-snug">{results[selected].title}</h3>
          </div>
          <div className="p-6 space-y-5">
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2 font-semibold">Reasoning</p>
              <p className="text-sm text-foreground/90 leading-relaxed">
                Matched on <span className="text-primary font-medium">jurisdiction (EU)</span>,
                <span className="text-primary font-medium"> transaction type (electronic payment)</span>, and
                <span className="text-primary font-medium"> threshold (≥ €30)</span>. Cross-referenced with 3 supporting RTS documents.
              </p>
            </div>

            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2 font-semibold">Source preview</p>
              <div className="rounded-xl border border-border bg-card/60 p-4">
                <div className="flex items-center gap-2 mb-3">
                  <FileText className="h-4 w-4 text-primary" />
                  <p className="text-xs font-mono text-muted-foreground">PSD2_Article_97.pdf · pg 142</p>
                </div>
                <p className="text-xs text-foreground/80 leading-relaxed italic">
                  "{results[selected].snippet}"
                </p>
                <Button variant="outline" size="sm" className="mt-3 w-full">
                  Open full source <ExternalLink className="h-3 w-3" />
                </Button>
              </div>
            </div>

            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2 font-semibold">Related rules</p>
              <div className="space-y-2">
                {["RTS on SCA Article 4", "EBA Guidelines EBA/GL/2022/03", "PSD2 Article 98"].map((rel) => (
                  <div key={rel} className="text-xs px-3 py-2 rounded-lg bg-secondary/60 hover:bg-secondary cursor-pointer transition-colors">
                    {rel}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </aside>
      )}
    </div>
  );
};

export default RuleSearch;
