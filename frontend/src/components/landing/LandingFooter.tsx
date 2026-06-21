import { Sparkles } from "lucide-react";

export function LandingFooter() {
  return (
    <footer className="bg-[hsl(var(--landing-nav))]">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-10 sm:flex-row sm:items-center sm:justify-between lg:px-8">
        <div className="flex items-center gap-2.5">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-gradient-primary">
            <Sparkles className="h-3 w-3 text-white" />
          </div>
          <span className="text-[10px] font-medium uppercase tracking-[0.18em] text-white/80">
            Lex Intelligence
          </span>
        </div>
        <p className="text-xs text-white/50">© 2026 Lex Intelligence, Inc.</p>
      </div>
    </footer>
  );
}
