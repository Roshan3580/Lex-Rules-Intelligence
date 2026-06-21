import { LandingSectionHeader } from "./LandingSectionHeader";

const capabilities = [
  "PDF / website / pasted text ingestion",
  "State and tax-type filtering",
  "Source-backed retrieval",
  "Confidence scoring",
  "Citation tracking",
  "Human review queue",
  "Audit trail",
  "Deterministic fallback when no LLM key is set",
];

export function CapabilitiesSection() {
  return (
    <section id="capabilities" className="border-b border-[hsl(var(--landing-border))]">
      <div className="mx-auto max-w-7xl px-6 py-20 lg:px-8 lg:py-24">
        <LandingSectionHeader
          label="Capabilities"
          title="Built for compliance teams who need evidence, not guesses"
          description="Lex degrades gracefully: without an LLM key, ingestion still chunks and heuristically extracts rules, and Q&A returns structured answers from retrieved rules with citations."
        />

        <div className="mt-14 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {capabilities.map((capability) => (
            <div key={capability} className="landing-card p-5">
              <p className="text-sm leading-relaxed text-[hsl(var(--landing-fg))]">{capability}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
