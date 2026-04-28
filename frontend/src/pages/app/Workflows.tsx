import { CheckCircle2, Circle, Clock, FileText, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

const steps = [
  {
    name: "Identity verification",
    status: "complete",
    rules: 4,
    docs: ["Passport", "Proof of address"],
    validations: ["Government ID format", "Document authenticity check"],
  },
  {
    name: "Beneficial ownership",
    status: "complete",
    rules: 3,
    docs: ["UBO declaration", "Corporate registry extract"],
    validations: ["≥25% threshold check", "PEP screening"],
  },
  {
    name: "Risk assessment",
    status: "active",
    rules: 7,
    docs: ["Source of funds statement"],
    validations: ["High-risk jurisdiction match", "Sanctions screening", "Industry risk score"],
  },
  {
    name: "Approval & submission",
    status: "pending",
    rules: 2,
    docs: ["Compliance officer sign-off"],
    validations: ["Senior management approval", "Audit log finalization"],
  },
];

const Workflows = () => {
  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-[1400px]">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <p className="text-xs uppercase tracking-widest text-muted-foreground">Case · #CS-2026-1847</p>
          <h1 className="text-3xl font-bold tracking-tight mt-1">Onboarding — Acme Capital GmbH</h1>
          <p className="text-sm text-muted-foreground mt-1">EU corporate · cross-border payments program · started 2 days ago</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">View audit trail</Button>
          <Button variant="hero" size="sm">Continue case</Button>
        </div>
      </div>

      {/* Progress tracker */}
      <div className="rounded-2xl glass p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Case progress</p>
            <p className="text-2xl font-bold mt-1">2 of 4 steps complete</p>
          </div>
          <span className="text-3xl font-bold gradient-text font-mono">50%</span>
        </div>
        <div className="h-2 rounded-full bg-secondary overflow-hidden">
          <div className="h-full w-1/2 bg-gradient-primary rounded-full transition-all" />
        </div>
        <div className="grid grid-cols-4 mt-3 gap-2">
          {steps.map((s) => (
            <div key={s.name} className="text-[10px] text-center text-muted-foreground truncate">{s.name}</div>
          ))}
        </div>
      </div>

      {/* Steps */}
      <div className="space-y-3">
        {steps.map((s, i) => (
          <div
            key={s.name}
            className={`rounded-2xl border p-6 transition-all ${
              s.status === "active"
                ? "border-primary/40 bg-card shadow-elegant"
                : s.status === "complete"
                ? "border-border/60 bg-card/40"
                : "border-border/40 bg-card/20"
            }`}
          >
            <div className="flex items-start gap-4">
              <div className={`mt-0.5 h-8 w-8 rounded-full flex items-center justify-center shrink-0 ${
                s.status === "complete" ? "bg-success/15 text-success" :
                s.status === "active" ? "bg-primary/15 text-primary animate-pulse-glow" :
                "bg-secondary text-muted-foreground"
              }`}>
                {s.status === "complete" ? <CheckCircle2 className="h-4 w-4" /> :
                 s.status === "active" ? <Clock className="h-4 w-4" /> :
                 <Circle className="h-4 w-4" />}
              </div>
              <div className="flex-1">
                <div className="flex items-start justify-between gap-4 mb-3">
                  <div>
                    <p className="text-[11px] uppercase tracking-wider text-muted-foreground font-mono">Step {i + 1}</p>
                    <h3 className="text-lg font-semibold mt-0.5">{s.name}</h3>
                  </div>
                  <span className={`text-[10px] uppercase tracking-wider font-semibold px-2 py-1 rounded ${
                    s.status === "complete" ? "bg-success/10 text-success" :
                    s.status === "active" ? "bg-primary/10 text-primary" :
                    "bg-secondary text-muted-foreground"
                  }`}>
                    {s.status}
                  </span>
                </div>

                <div className="grid md:grid-cols-3 gap-4 mt-4">
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2 font-semibold">
                      Rules applied · <span className="text-primary">{s.rules}</span>
                    </p>
                    <p className="text-xs text-muted-foreground">Auto-applied from rule index</p>
                  </div>
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2 font-semibold">Required documents</p>
                    <ul className="space-y-1">
                      {s.docs.map((d) => (
                        <li key={d} className="text-xs flex items-center gap-1.5">
                          <FileText className="h-3 w-3 text-muted-foreground" /> {d}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2 font-semibold">Validations</p>
                    <ul className="space-y-1">
                      {s.validations.map((v) => (
                        <li key={v} className="text-xs flex items-center gap-1.5">
                          {s.status === "complete" ? (
                            <CheckCircle2 className="h-3 w-3 text-success" />
                          ) : s.status === "active" ? (
                            <AlertCircle className="h-3 w-3 text-warning" />
                          ) : (
                            <Circle className="h-3 w-3 text-muted-foreground" />
                          )}
                          {v}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Workflows;
