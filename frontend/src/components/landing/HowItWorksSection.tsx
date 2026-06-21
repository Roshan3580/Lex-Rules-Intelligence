import { ArrowRight } from "lucide-react";
import { LandingSectionHeader } from "./LandingSectionHeader";

const steps = [
  { title: "Source ingestion", body: "PDFs, URLs, uploads, and pasted text enter the pipeline." },
  { title: "Rule extraction", body: "Hybrid LLM + heuristic extraction with structured fields." },
  { title: "Retrieval", body: "State and tax-type filters narrow relevant rules and chunks." },
  { title: "Cited answer", body: "Grounded responses with sources, snippets, and confidence." },
  { title: "Human review", body: "Low-confidence outputs route to approve / reject / publish." },
  { title: "Workflow output", body: "Validated rules feed search, validation, and audit flows." },
];

export function HowItWorksSection() {
  return (
    <section id="how-it-works" className="border-b border-[hsl(var(--landing-border))] bg-white">
      <div className="mx-auto max-w-7xl px-6 py-20 lg:px-8 lg:py-24">
        <LandingSectionHeader
          label="How it works"
          title="A governed pipeline from ingestion to workflow delivery"
          description="Each stage preserves source traceability — every rule carries source_id, document name, URL, and a literal snippet."
        />

        <div className="mt-14 overflow-x-auto">
          <div className="flex min-w-[920px] items-stretch gap-3">
            {steps.map((step, index) => (
              <div key={step.title} className="flex min-w-0 flex-1 items-stretch">
                <div className="landing-card flex min-w-0 flex-1 flex-col p-5">
                  <p className="landing-label mb-3">Step {index + 1}</p>
                  <h3 className="text-sm font-medium text-[hsl(var(--landing-fg))]">{step.title}</h3>
                  <p className="mt-2 text-xs leading-relaxed text-[hsl(var(--landing-muted))]">
                    {step.body}
                  </p>
                </div>
                {index < steps.length - 1 && (
                  <div className="flex w-6 shrink-0 items-center justify-center text-[hsl(var(--landing-muted))]">
                    <ArrowRight className="h-4 w-4" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
