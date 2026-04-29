import { ChevronRight, PartyPopper } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const steps = [
  { title: "Ingest sources", path: "/app/sources", body: "URL / PDF → chunks → extraction run." },
  { title: "Review & publish rules", path: "/app/review", body: "Human approve before enforcement." },
  { title: "Validate submission", path: "/app/validate", body: "Deterministic gates (no LLM on path)." },
  { title: "Log rejection outcome", path: "/app/outcomes", body: "Close the loop on coverage." },
  { title: "Analytics", path: "/app/analytics", body: "Volume + rejection coverage trends." },
];

export default function DemoGuide() {
  return (
    <div className="p-6 lg:p-8 max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
          <PartyPopper className="h-6 w-6" />
          Guided demo (~5 min)
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Optional reset: <code className="text-xs">POST /api/demo/reset</code> with{" "}
          <code className="text-xs">DEMO_MODE=true</code>.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Flow</CardTitle>
          <CardDescription>Investor-ready narrative on the existing stack.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {steps.map((s) => (
            <div
              key={s.path}
              className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-border/80 p-4"
            >
              <div>
                <div className="font-medium text-foreground">{s.title}</div>
                <p className="text-sm text-muted-foreground mt-1">{s.body}</p>
              </div>
              <Button asChild variant="outline" size="sm" className="shrink-0">
                <Link to={s.path}>
                  Open <ChevronRight className="h-4 w-4 ml-1" />
                </Link>
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
