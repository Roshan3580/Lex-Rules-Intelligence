import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { StatusCards } from "./StatusCards";

const trustRow = ["50 states", "Source-backed answers", "Human review queue"];

export function LandingHero() {
  return (
    <section className="relative border-b border-[hsl(var(--landing-border))]">
      <div className="absolute inset-0 landing-grid-bg opacity-60" />

      <div className="relative mx-auto grid max-w-7xl gap-12 px-6 py-16 lg:grid-cols-[1.05fr_0.95fr] lg:items-start lg:gap-10 lg:px-8 lg:py-24">
        <div className="max-w-xl">
          <p className="landing-label mb-6">Source-backed rules intelligence</p>

          <h1 className="font-serif text-[2.75rem] leading-[1.02] tracking-tight text-[hsl(var(--landing-fg))] sm:text-6xl lg:text-[4.25rem]">
            See every rule.
            <br />
            Answer every filing.
          </h1>

          <p className="mt-6 text-base leading-relaxed text-[hsl(var(--landing-muted))] md:text-lg">
            Lex ingests fragmented state tax law from PDFs, regulator sites, uploads, and pasted
            text — extracts structured rules, cites every source, and routes low-confidence answers
            to human review.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
            <Link
              to="/app/search"
              className="inline-flex items-center justify-center gap-2 bg-[hsl(var(--landing-nav))] px-6 py-3.5 text-[11px] font-medium uppercase tracking-[0.16em] text-white transition-opacity hover:opacity-90"
            >
              Start querying rules
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
            <Link
              to="/app"
              className="inline-flex items-center justify-center border border-[hsl(var(--landing-border))] bg-white px-6 py-3.5 text-[11px] font-medium uppercase tracking-[0.16em] text-[hsl(var(--landing-fg))] transition-colors hover:border-[hsl(var(--landing-fg))]"
            >
              View live dashboard
            </Link>
          </div>

          <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2 border-t border-[hsl(var(--landing-border))] pt-6">
            {trustRow.map((item) => (
              <span
                key={item}
                className="text-[10px] font-medium uppercase tracking-[0.16em] text-[hsl(var(--landing-muted))]"
              >
                {item}
              </span>
            ))}
          </div>
        </div>

        <StatusCards />
      </div>
    </section>
  );
}
