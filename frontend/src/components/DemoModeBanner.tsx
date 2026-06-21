import { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";

/**
 * Thin banner that appears only when the backend reports demo_mode=true.
 * Demo mode means the illustrative CA/TX/NY seed rules are loaded — useful
 * for showing the app off, but the rules are placeholder content, not
 * authoritative tax law.
 */
export function DemoModeBanner() {
  const [demo, setDemo] = useState(false);

  useEffect(() => {
    api
      .health()
      .then((h) => setDemo(Boolean(h.demo_mode)))
      .catch(() => setDemo(false));
  }, []);

  if (!demo) return null;

  return (
    <div className="bg-amber-50 border-b border-amber-200 text-amber-900 text-xs px-4 py-2 flex items-center gap-2">
      <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
      <span className="font-semibold uppercase tracking-wider">Demo mode</span>
      <span className="text-amber-800">
        Illustrative CA / TX / NY rules are loaded for demonstration. They are
        placeholder content, not authoritative tax law. Set{" "}
        <code className="font-mono px-1 bg-amber-100 rounded">DEMO_MODE=false</code>{" "}
        and clear the database to start from real ingested sources.
      </span>
    </div>
  );
}
