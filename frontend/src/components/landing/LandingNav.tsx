import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";

const navLinks = [
  { label: "Platform", href: "#platform" },
  { label: "How it works", href: "#how-it-works" },
  { label: "Capabilities", href: "#capabilities" },
  { label: "Trust", href: "#trust" },
];

export function LandingNav() {
  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-[hsl(var(--landing-nav))]">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6 lg:px-8">
        <Link to="/" className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-gradient-primary">
            <Sparkles className="h-3.5 w-3.5 text-white" />
          </div>
          <span className="text-[11px] font-medium uppercase tracking-[0.22em] text-white">
            Lex Intelligence
          </span>
        </Link>

        <nav className="hidden items-center gap-8 md:flex">
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-[10px] font-medium uppercase tracking-[0.18em] text-white/70 transition-colors hover:text-white"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <Link
          to="/app"
          className="border border-white/30 px-4 py-2 text-[10px] font-medium uppercase tracking-[0.18em] text-white transition-colors hover:border-white hover:bg-white hover:text-[hsl(var(--landing-nav))]"
        >
          Open App
        </Link>
      </div>

      <nav className="flex gap-5 overflow-x-auto border-t border-white/10 px-6 py-2.5 md:hidden">
        {navLinks.map((link) => (
          <a
            key={link.href}
            href={link.href}
            className="shrink-0 text-[10px] font-medium uppercase tracking-[0.16em] text-white/60"
          >
            {link.label}
          </a>
        ))}
      </nav>
    </header>
  );
}
