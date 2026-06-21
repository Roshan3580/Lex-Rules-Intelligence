const statusCards = [
  { label: "States Covered", value: "50" },
  { label: "Rule Intelligence", value: "Source-backed" },
  { label: "System", value: "Live Demo", live: true },
  { label: "Review Layer", value: "Human-in-the-loop" },
  { label: "Retrieval", value: "Citation-aware" },
  { label: "Sources", value: "PDFs / websites / uploads" },
];

const statusStrip = [
  "RAG engine online",
  "Sources streaming",
  "Review queue enabled",
];

export function StatusCards() {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div className="landing-card col-span-2 p-5 md:col-span-1 md:row-span-2 md:flex md:flex-col md:justify-between">
          <p className="landing-label">{statusCards[0].label}</p>
          <p className="mt-8 font-serif text-5xl leading-none tracking-tight text-[hsl(var(--landing-fg))] md:mt-0 md:text-6xl">
            {statusCards[0].value}
          </p>
        </div>

        {statusCards.slice(1, 3).map((card) => (
          <div key={card.label} className="landing-card p-4">
            <p className="landing-label">{card.label}</p>
            <div className="mt-3 flex items-center gap-2">
              {card.live && (
                <span className="h-1.5 w-1.5 rounded-full bg-[hsl(var(--landing-accent))]" />
              )}
              <p className="font-serif text-xl leading-tight text-[hsl(var(--landing-fg))] md:text-2xl">
                {card.value}
              </p>
            </div>
          </div>
        ))}

        {statusCards.slice(3).map((card) => (
          <div key={card.label} className="landing-card p-4">
            <p className="landing-label">{card.label}</p>
            <p className="mt-3 font-serif text-lg leading-tight text-[hsl(var(--landing-fg))] md:text-xl">
              {card.value}
            </p>
          </div>
        ))}
      </div>

      <div className="landing-card flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-x-5 gap-y-2">
          {statusStrip.map((item) => (
            <span
              key={item}
              className="flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.14em] text-[hsl(var(--landing-muted))]"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-[hsl(var(--landing-accent))]" />
              {item}
            </span>
          ))}
        </div>
        <div className="hidden h-px flex-1 bg-[hsl(var(--landing-border))] sm:block" />
        <div className="h-1 w-full overflow-hidden bg-[hsl(var(--landing-border))] sm:w-24">
          <div className="h-full w-2/3 bg-[hsl(var(--landing-accent))]" />
        </div>
      </div>
    </div>
  );
}
