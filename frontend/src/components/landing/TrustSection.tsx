import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { LandingSectionHeader } from "./LandingSectionHeader";

const trustPoints = [
  {
    title: "Source grounding",
    body: "Answers are assembled from retrieved rules and source chunks — not invented tax guidance.",
  },
  {
    title: "Citations on every response",
    body: "Each answer links back to document title, URL, snippet, and last_checked timestamp.",
  },
  {
    title: "Reviewable outputs",
    body: "Extracted rules enter a review queue with approve, reject, publish, and needs_review actions.",
  },
  {
    title: "Confidence scoring",
    body: "Transparent confidence scores help teams decide when to trust, verify, or escalate.",
  },
  {
    title: "Human-in-the-loop workflows",
    body: "Publishing is governed: rules must pass validation and meet confidence thresholds.",
  },
  {
    title: "Auditability",
    body: "Review events and outcome tracking provide an immutable trail of who changed what.",
  },
];

export function TrustSection() {
  return (
    <section id="trust" className="border-b border-[hsl(var(--landing-border))] bg-white">
      <div className="mx-auto max-w-7xl px-6 py-20 lg:px-8 lg:py-24">
        <LandingSectionHeader
          label="Trust"
          title="Designed for teams who must show their work"
          description="Lex prioritizes traceability over flash. No certification claims — just source-backed intelligence you can inspect."
        />

        <div className="mt-14 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {trustPoints.map((point) => (
            <div key={point.title} className="landing-card p-6">
              <h3 className="text-sm font-medium text-[hsl(var(--landing-fg))]">{point.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-[hsl(var(--landing-muted))]">
                {point.body}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-16 border border-[hsl(var(--landing-border))] bg-[hsl(40_20%_98%)] p-8 md:p-10">
          <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="landing-label mb-3">Get started</p>
              <h3 className="font-serif text-2xl tracking-tight text-[hsl(var(--landing-fg))] md:text-3xl">
                Open the app and query your own sources
              </h3>
              <p className="mt-3 max-w-xl text-sm text-[hsl(var(--landing-muted))]">
                Try ingestion, search, review, and validation flows on the live dashboard.
              </p>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row">
              <Link
                to="/app"
                className="inline-flex items-center justify-center gap-2 bg-[hsl(var(--landing-nav))] px-6 py-3.5 text-[11px] font-medium uppercase tracking-[0.16em] text-white transition-opacity hover:opacity-90"
              >
                Open the dashboard
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
              <a
                href="mailto:roshar1@uci.edu"
                className="inline-flex items-center justify-center border border-[hsl(var(--landing-border))] bg-white px-6 py-3.5 text-[11px] font-medium uppercase tracking-[0.16em] text-[hsl(var(--landing-fg))] transition-colors hover:border-[hsl(var(--landing-fg))]"
              >
                Contact us
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
