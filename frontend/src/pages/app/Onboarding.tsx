import { ClipboardList, Sparkles } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useEffect, useState } from "react";
import { api, type KpiSummary } from "@/lib/api";

export default function Onboarding() {
  const [kpis, setKpis] = useState<KpiSummary | null>(null);

  useEffect(() => {
    api.platformKpis().then(setKpis).catch(() => setKpis(null));
  }, []);

  return (
    <div className="p-6 lg:p-8 max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
          <ClipboardList className="h-6 w-6" />
          Client onboarding
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Wire sources → workflows → reviewer roles; monitor KPIs once traffic lands.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Sparkles className="h-5 w-5" /> Steps
          </CardTitle>
          <CardDescription>Same modular monolith — no separate control plane.</CardDescription>
        </CardHeader>
        <CardContent className="prose prose-sm dark:prose-invert space-y-3 text-muted-foreground">
          <ol className="list-decimal pl-5 space-y-2">
            <li>Ingest authoritative sources (<strong className="text-foreground">Sources</strong>).</li>
            <li>
              Review &amp; publish rules (<strong className="text-foreground">Review Queue</strong>).
            </li>
            <li>
              Map workflows (<strong className="text-foreground">Workflows</strong>) against state programs.
            </li>
            <li>
              Use <strong className="text-foreground">Submission path</strong> / <strong className="text-foreground">Validator</strong>{" "}
              to prove deterministic enforcement.
            </li>
            <li>
              Tenant scoping defaults to <code>default</code> — extend FK + policies when hardening tenancy.
            </li>
          </ol>
          {kpis && (
            <div className="not-prose rounded-xl border border-border p-4 grid grid-cols-3 gap-4 text-center text-sm mt-4">
              <div>
                <div className="text-muted-foreground">Published rules</div>
                <div className="text-lg font-semibold text-foreground">{kpis.rules_published}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Outcomes</div>
                <div className="text-lg font-semibold text-foreground">{kpis.outcome_events}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Active sources</div>
                <div className="text-lg font-semibold text-foreground">{kpis.active_sources}</div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
