import { LandingSectionHeader } from "./LandingSectionHeader";

const columns = [
  {
    title: "Sources",
    items: [
      "PDFs",
      "Regulator websites",
      "APIs",
      "Pasted text",
      "Uploaded documents",
    ],
  },
  {
    title: "Processing",
    items: [
      "Extraction",
      "Validation",
      "Deduplication",
      "Retrieval",
      "Confidence scoring",
    ],
  },
  {
    title: "Output",
    items: [
      "Cited answers",
      "Rule records",
      "Review queue",
      "Audit trail",
    ],
  },
];

export function PlatformSection() {
  return (
    <section id="platform" className="border-b border-[hsl(var(--landing-border))]">
      <div className="mx-auto max-w-7xl px-6 py-20 lg:px-8 lg:py-24">
        <LandingSectionHeader
          label="Platform"
          title="From fragmented sources to reviewable operational intelligence"
          description="Lex is not a chatbot wrapper. Every answer is grounded in indexed sources, returns citations and confidence, and routes low-confidence rules to human review."
        />

        <div className="mt-14 grid gap-4 md:grid-cols-3">
          {columns.map((column) => (
            <div key={column.title} className="landing-card p-6">
              <p className="landing-label mb-5">{column.title}</p>
              <ul className="space-y-3">
                {column.items.map((item) => (
                  <li
                    key={item}
                    className="border-t border-[hsl(var(--landing-border))] pt-3 text-sm text-[hsl(var(--landing-fg))] first:border-t-0 first:pt-0"
                  >
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
