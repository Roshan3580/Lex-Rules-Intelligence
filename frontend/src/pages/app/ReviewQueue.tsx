import { useState } from "react";
import { Check, X, Edit3, FileText, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Confidence } from "@/components/Confidence";

const queue = [
  { id: 1, rule: "EDD required for transactions over €10K to high-risk countries", source: "AML Directive Art. 18", conf: 58, status: "draft", assignee: "S. Park" },
  { id: 2, rule: "Annual beneficial ownership refresh mandatory", source: "FATF Rec. 24", conf: 72, status: "in_review", assignee: "M. Chen" },
  { id: 3, rule: "PEP screening at onboarding and continuously thereafter", source: "AMLD5 Art. 20", conf: 61, status: "draft", assignee: "—" },
  { id: 4, rule: "Suspicious activity reports within 30 days of detection", source: "BSA §5318(g)", conf: 84, status: "in_review", assignee: "A. Cole" },
  { id: 5, rule: "Customer identification program required for new accounts", source: "CIP Rule 31 CFR 1020.220", conf: 92, status: "in_review", assignee: "S. Park" },
];

const ReviewQueue = () => {
  const [selected, setSelected] = useState(0);
  const item = queue[selected];

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* List */}
      <div className="w-full lg:w-[460px] shrink-0 border-r border-border overflow-y-auto">
        <div className="p-5 border-b border-border sticky top-0 bg-background/80 backdrop-blur-xl z-10">
          <p className="text-xs uppercase tracking-widest text-muted-foreground">Human-in-the-loop</p>
          <h1 className="text-2xl font-bold tracking-tight mt-1">Review queue</h1>
          <div className="flex items-center gap-3 mt-3">
            <span className="text-xs px-2 py-1 rounded-md bg-warning/10 text-warning border border-warning/20">
              12 pending
            </span>
            <span className="text-xs text-muted-foreground">avg time to review · 4m</span>
          </div>
        </div>
        <div>
          {queue.map((q, i) => (
            <button
              key={q.id}
              onClick={() => setSelected(i)}
              className={`w-full text-left p-5 border-b border-border/40 hover:bg-secondary/30 transition-colors ${
                selected === i ? "bg-secondary/50 border-l-2 border-l-primary" : ""
              }`}
            >
              <div className="flex items-start justify-between gap-3 mb-2">
                <p className="text-sm font-medium leading-snug">{q.rule}</p>
                <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
              </div>
              <p className="text-[11px] text-muted-foreground font-mono mb-3">{q.source}</p>
              <div className="flex items-center justify-between">
                <Confidence value={q.conf} size="sm" />
                <span className={`text-[10px] uppercase tracking-wider font-semibold ${
                  q.status === "draft" ? "text-muted-foreground" : "text-teal"
                }`}>
                  {q.status.replace("_", " ")}
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Detail */}
      <div className="hidden lg:flex flex-1 flex-col overflow-hidden">
        <div className="p-6 border-b border-border">
          <div className="flex items-start justify-between gap-4 mb-3">
            <div>
              <p className="text-[11px] uppercase tracking-widest text-muted-foreground mb-1">Extraction #{item.id}</p>
              <h2 className="text-xl font-semibold leading-snug">{item.rule}</h2>
            </div>
            <Confidence value={item.conf} />
          </div>
          <div className="flex items-center gap-2">
            <Button variant="hero" size="sm"><Check className="h-3.5 w-3.5" /> Approve</Button>
            <Button variant="outline" size="sm"><Edit3 className="h-3.5 w-3.5" /> Edit</Button>
            <Button variant="outline" size="sm" className="text-destructive hover:text-destructive">
              <X className="h-3.5 w-3.5" /> Reject
            </Button>
          </div>
        </div>

        <div className="flex-1 grid grid-cols-2 overflow-hidden">
          {/* Source snippet */}
          <div className="border-r border-border overflow-y-auto p-6">
            <div className="flex items-center gap-2 mb-4">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <p className="text-xs font-mono text-muted-foreground">{item.source}</p>
            </div>
            <div className="rounded-xl border border-border bg-card/60 p-5 space-y-3">
              <p className="text-xs text-muted-foreground leading-relaxed">
                ...obliged entities shall apply, in addition to the customer due diligence measures laid down in
                Article 13, enhanced customer due diligence measures in business relationships or transactions
                involving high-risk third countries identified pursuant to Article 9(2)...
              </p>
              <div className="rounded-lg bg-primary/10 border-l-2 border-primary p-3">
                <p className="text-xs text-foreground leading-relaxed">
                  <span className="bg-primary/20 px-0.5 rounded">Member States shall require obliged entities to apply
                  enhanced customer due diligence measures</span> in business relationships and transactions involving
                  high-risk third countries...
                </p>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                ...the measures referred to in paragraph 1 shall include at least: obtaining additional information
                on the customer and on the beneficial owner...
              </p>
            </div>
          </div>

          {/* Extracted */}
          <div className="overflow-y-auto p-6 bg-secondary/20">
            <p className="text-xs uppercase tracking-wider text-primary font-semibold mb-4 flex items-center gap-1.5">
              Extracted rule
            </p>
            <div className="space-y-5">
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5 font-semibold">Summary</p>
                <p className="text-sm">{item.rule}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5 font-semibold">Conditions</p>
                <ul className="space-y-1.5">
                  {["Counterparty in high-risk country list", "Transaction value > €10,000", "Business relationship active"].map((c) => (
                    <li key={c} className="text-sm flex items-start gap-2">
                      <span className="mt-1.5 h-1 w-1 rounded-full bg-teal shrink-0" />
                      {c}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5 font-semibold">Required actions</p>
                <ul className="space-y-1.5">
                  {["Senior management approval", "Establish source of funds", "Enhanced ongoing monitoring"].map((a) => (
                    <li key={a} className="text-sm flex items-start gap-2">
                      <span className="mt-1.5 h-1 w-1 rounded-full bg-primary shrink-0" />
                      {a}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="rounded-xl border border-warning/30 bg-warning/5 p-4">
                <p className="text-xs font-semibold text-warning mb-1">Why low confidence?</p>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Threshold (€10K) was inferred from contextual paragraph 4. Original article does not state explicit amount.
                  Recommend manual verification.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReviewQueue;
