import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Sparkles,
  ArrowRight,
  FileText,
  Search,
  CheckCircle2,
  Workflow,
  Shield,
  Zap,
  GitBranch,
  Database,
  Activity,
} from "lucide-react";

const Landing = () => {
  return (
    <div className="min-h-screen bg-background overflow-hidden">
      {/* Nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-border/40 bg-background/70 backdrop-blur-xl">
        <div className="container mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-gradient-primary flex items-center justify-center shadow-glow">
              <Sparkles className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="font-semibold tracking-tight">Lex</span>
            <span className="hidden sm:inline text-[10px] uppercase tracking-widest text-muted-foreground border border-border rounded px-1.5 py-0.5">
              Intelligence
            </span>
          </Link>
          <div className="hidden md:flex items-center gap-8 text-sm text-muted-foreground">
            <a href="#features" className="hover:text-foreground transition-colors">Features</a>
            <a href="#pipeline" className="hover:text-foreground transition-colors">How it works</a>
            <a href="#trust" className="hover:text-foreground transition-colors">Trust</a>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" className="hidden sm:inline-flex">Sign in</Button>
            <Button asChild variant="hero" size="sm">
              <Link to="/app">
                Open app <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </Button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative pt-32 pb-24 lg:pt-40 lg:pb-32">
        <div className="absolute inset-0 grid-bg pointer-events-none" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-gradient-glow pointer-events-none" />

        <div className="container relative mx-auto px-6">
          <div className="max-w-4xl mx-auto text-center">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full glass mb-8 animate-fade-in">
              <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" />
              <span className="text-xs text-muted-foreground">Now in private beta — </span>
              <span className="text-xs text-foreground font-medium">SOC 2 Type II ready</span>
            </div>

            <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight leading-[1.05] animate-fade-in-up">
              Turn fragmented rules into <br />
              <span className="gradient-text">operational intelligence</span>
            </h1>

            <p className="mt-6 text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto animate-fade-in-up" style={{ animationDelay: "0.1s" }}>
              Lex ingests rules from PDFs, websites, and APIs — extracts, validates, and delivers them to the
              workflows your operations and compliance teams already run.
            </p>

            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3 animate-fade-in-up" style={{ animationDelay: "0.2s" }}>
              <Button asChild variant="hero" size="xl">
                <Link to="/app/search">
                  Start querying rules <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button asChild variant="outline" size="xl">
                <Link to="/app">View live dashboard</Link>
              </Button>
            </div>

            <p className="mt-6 text-xs text-muted-foreground">
              No credit card. Trusted by compliance teams at high-growth fintech & insurance.
            </p>
          </div>

          {/* Hero visual: pipeline mock */}
          <div className="mt-20 max-w-5xl mx-auto animate-fade-in-up" style={{ animationDelay: "0.3s" }}>
            <div className="relative rounded-2xl glass-strong p-2 shadow-elegant">
              <div className="absolute -inset-px rounded-2xl bg-gradient-primary opacity-20 blur-xl pointer-events-none" />
              <div className="relative rounded-xl bg-card/80 border border-border/60 overflow-hidden">
                {/* Window chrome */}
                <div className="flex items-center gap-2 px-4 h-9 border-b border-border/60 bg-background/40">
                  <div className="flex gap-1.5">
                    <div className="h-2.5 w-2.5 rounded-full bg-destructive/60" />
                    <div className="h-2.5 w-2.5 rounded-full bg-warning/60" />
                    <div className="h-2.5 w-2.5 rounded-full bg-success/60" />
                  </div>
                  <div className="ml-4 text-[11px] text-muted-foreground font-mono">lex.app/search</div>
                </div>
                <div className="p-6 md:p-8 space-y-6">
                  {/* AI input */}
                  <div className="rounded-xl border border-primary/30 bg-secondary/40 p-4 shadow-glow">
                    <div className="flex items-start gap-3">
                      <Sparkles className="h-5 w-5 text-primary mt-0.5" />
                      <div className="flex-1">
                        <p className="text-sm text-foreground">
                          What rules apply to cross-border B2B payments above $10K in the EU?
                        </p>
                        <div className="mt-2 flex gap-2">
                          <span className="text-[10px] px-2 py-0.5 rounded bg-primary/15 text-primary border border-primary/20">
                            jurisdiction: EU
                          </span>
                          <span className="text-[10px] px-2 py-0.5 rounded bg-teal/15 text-teal border border-teal/20">
                            program: payments
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                  {/* Result cards */}
                  <div className="grid md:grid-cols-2 gap-3">
                    {[
                      { title: "PSD2 Strong Customer Authentication", conf: 96, src: "EUR-Lex 2015/2366", tone: "success" },
                      { title: "AML Beneficial Ownership Disclosure", conf: 88, src: "FATF Recommendation 24", tone: "success" },
                    ].map((r) => (
                      <div key={r.title} className="rounded-lg border border-border bg-card/60 p-4 hover:border-primary/40 transition-colors">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-sm font-medium text-foreground leading-snug">{r.title}</p>
                          <CheckCircle2 className="h-4 w-4 text-success shrink-0" />
                        </div>
                        <p className="text-[11px] text-muted-foreground mt-2 font-mono">{r.src}</p>
                        <div className="mt-3 flex items-center gap-2">
                          <div className="h-1 flex-1 rounded-full bg-secondary overflow-hidden">
                            <div className="h-full bg-success" style={{ width: `${r.conf}%` }} />
                          </div>
                          <span className="text-[11px] font-mono text-success">{r.conf}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Logos */}
          <div className="mt-16 text-center">
            <p className="text-[11px] uppercase tracking-widest text-muted-foreground/60 mb-6">
              Trusted by operations teams
            </p>
            <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-4 opacity-50">
              {["NORTHWIND", "ACME CAPITAL", "MERIDIAN", "VANTA HEALTH", "ATLAS PAY", "LUMEN"].map((l) => (
                <span key={l} className="text-sm font-bold tracking-widest text-muted-foreground">{l}</span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Pipeline */}
      <section id="pipeline" className="py-24 border-t border-border/40">
        <div className="container mx-auto px-6">
          <div className="max-w-2xl mx-auto text-center mb-16">
            <p className="text-xs uppercase tracking-widest text-primary mb-3">How it works</p>
            <h2 className="text-3xl md:text-5xl font-bold tracking-tight">
              From raw documents to <span className="gradient-text">live workflows</span>
            </h2>
            <p className="mt-4 text-muted-foreground">
              A continuously-running pipeline that keeps your teams in sync with the regulations that matter.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {[
              {
                step: "01",
                icon: Database,
                title: "Ingest",
                body: "Connect PDFs, regulator websites, and APIs. We monitor changes 24/7.",
              },
              {
                step: "02",
                icon: Sparkles,
                title: "Extract & validate",
                body: "AI extracts structured rules with confidence scoring and source citations.",
              },
              {
                step: "03",
                icon: Workflow,
                title: "Operationalize",
                body: "Push validated rules into your review queues, checklists, and workflows.",
              },
            ].map((s, i) => (
              <div key={s.step} className="relative group">
                <div className="relative h-full rounded-2xl glass p-6 hover:border-primary/40 transition-all hover:-translate-y-1">
                  <div className="flex items-center justify-between mb-6">
                    <span className="text-xs font-mono text-muted-foreground">{s.step}</span>
                    <div className="h-10 w-10 rounded-xl bg-gradient-primary/20 border border-primary/30 flex items-center justify-center">
                      <s.icon className="h-5 w-5 text-primary" />
                    </div>
                  </div>
                  <h3 className="text-lg font-semibold mb-2">{s.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{s.body}</p>
                </div>
                {i < 2 && (
                  <ArrowRight className="hidden md:block absolute top-1/2 -right-3 -translate-y-1/2 h-5 w-5 text-muted-foreground/40 z-10" />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24 border-t border-border/40 relative">
        <div className="container mx-auto px-6">
          <div className="max-w-2xl mb-16">
            <p className="text-xs uppercase tracking-widest text-primary mb-3">Capabilities</p>
            <h2 className="text-3xl md:text-5xl font-bold tracking-tight">
              Everything ops & compliance needs to move fast — without breaking rules.
            </h2>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { icon: Search, title: "Semantic rule search", body: "Ask questions in natural language. Get structured answers with citations." },
              { icon: Shield, title: "Confidence scoring", body: "Every extraction comes with a transparent confidence score and reasoning." },
              { icon: GitBranch, title: "Source traceability", body: "Click any rule to see the exact paragraph it came from. Always." },
              { icon: Workflow, title: "Workflow delivery", body: "Push rules into checklists, approval flows, and case management." },
              { icon: Activity, title: "Change monitoring", body: "Get alerted the moment a regulator updates a referenced source." },
              { icon: Zap, title: "Audit-ready logs", body: "Immutable history of who saw what, when, and which rule version applied." },
            ].map((f) => (
              <div key={f.title} className="group rounded-2xl glass p-6 hover:border-primary/40 transition-all">
                <div className="h-9 w-9 rounded-lg bg-secondary border border-border flex items-center justify-center mb-4 group-hover:bg-gradient-primary group-hover:border-transparent transition-all">
                  <f.icon className="h-4 w-4 text-primary group-hover:text-primary-foreground" />
                </div>
                <h3 className="text-base font-semibold mb-1.5">{f.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{f.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Trust */}
      <section id="trust" className="py-24 border-t border-border/40">
        <div className="container mx-auto px-6">
          <div className="grid lg:grid-cols-3 gap-6">
            {[
              { stat: "99.2%", label: "Extraction accuracy", body: "Benchmarked across 12K rules from 6 jurisdictions." },
              { stat: "<3min", label: "Average ingestion time", body: "From PDF upload to validated, queryable rule." },
              { stat: "100%", label: "Source traceability", body: "Every rule links to the originating paragraph." },
            ].map((t) => (
              <div key={t.label} className="rounded-2xl gradient-border p-8">
                <div className="text-5xl font-bold gradient-text tracking-tight">{t.stat}</div>
                <p className="mt-3 text-sm font-medium">{t.label}</p>
                <p className="mt-1 text-sm text-muted-foreground">{t.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 border-t border-border/40">
        <div className="container mx-auto px-6">
          <div className="relative rounded-3xl overflow-hidden glass-strong p-12 md:p-16 text-center">
            <div className="absolute inset-0 bg-gradient-glow opacity-60 pointer-events-none" />
            <div className="relative">
              <FileText className="h-10 w-10 text-primary mx-auto mb-6" />
              <h2 className="text-3xl md:text-5xl font-bold tracking-tight max-w-2xl mx-auto">
                Ready to operationalize your rules?
              </h2>
              <p className="mt-4 text-muted-foreground max-w-xl mx-auto">
                See how Lex transforms your regulatory workload in a 20-minute walkthrough.
              </p>
              <div className="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
                <Button asChild variant="hero" size="xl">
                  <Link to="/app">Open the dashboard <ArrowRight className="h-4 w-4" /></Link>
                </Button>
                <Button variant="outline" size="xl">Book a demo</Button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-border/40 py-10">
        <div className="container mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <div className="h-6 w-6 rounded bg-gradient-primary flex items-center justify-center">
              <Sparkles className="h-3 w-3 text-primary-foreground" />
            </div>
            <span>© 2026 Lex Intelligence, Inc.</span>
          </div>
          <div className="flex items-center gap-6 text-sm text-muted-foreground">
            <a href="#" className="hover:text-foreground">Security</a>
            <a href="#" className="hover:text-foreground">Privacy</a>
            <a href="#" className="hover:text-foreground">Terms</a>
            <a href="#" className="hover:text-foreground">Status</a>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
