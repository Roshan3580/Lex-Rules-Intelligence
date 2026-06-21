import { useState } from "react";
import { GitBranch, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api, type CaseWorkflow, type WorkflowAdvanceResponse } from "@/lib/api";

export default function WorkflowRunner() {
  const [state, setState] = useState("California");
  const [tax, setTax] = useState("sales_tax");
  const [caseId, setCaseId] = useState("");
  const [documents, setDocuments] = useState("Form ST-100");
  const [busy, setBusy] = useState(false);
  const [cw, setCw] = useState<CaseWorkflow | null>(null);
  const [last, setLast] = useState<WorkflowAdvanceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    setBusy(true);
    setError(null);
    try {
      const docs = documents.split(",").map((s) => s.trim()).filter(Boolean);
      const payload = await api.workflowStart({
        state,
        tax_category: tax,
        title: `${state} runner`,
        validation_payload: { documents: docs, amount: 1000, entity_type: "LLC" },
      });
      setCw(payload);
      setCaseId(payload.case_id);
      setLast(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function advance() {
    if (!caseId) return;
    setBusy(true);
    setError(null);
    try {
      const docs = documents.split(",").map((s) => s.trim()).filter(Boolean);
      const res = await api.workflowAdvance(caseId, {
        validation_payload: { documents: docs, amount: 1000, entity_type: "LLC" },
        actor: "demo",
      });
      setLast(res);
      if (res.case && typeof res.case === "object" && "case_id" in res.case) {
        setCw(res.case as CaseWorkflow);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="p-6 lg:p-8 max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="font-serif text-2xl leading-tight tracking-tight flex items-center gap-2">
          <GitBranch className="h-6 w-6" />
          Workflow runner
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          <code className="text-xs">POST /api/workflows/start</code> then{" "}
          <code className="text-xs">POST /api/workflows/{"{case_id}"}/advance</code> — advances only if deterministic validation passes.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Start</CardTitle>
          <CardDescription>Creates a case with a validation payload snapshot.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label>State</Label>
            <Input value={state} onChange={(e) => setState(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Tax category</Label>
            <Input value={tax} onChange={(e) => setTax(e.target.value)} />
          </div>
          <div className="space-y-2 sm:col-span-2">
            <Label>Documents (comma-separated)</Label>
            <Input value={documents} onChange={(e) => setDocuments(e.target.value)} />
          </div>
          <div className="sm:col-span-2 flex flex-wrap gap-2">
            <Button type="button" onClick={start} disabled={busy}>
              {busy && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Start workflow
            </Button>
            <Button type="button" variant="secondary" onClick={advance} disabled={busy || !caseId}>
              Advance (validate → complete step)
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {cw && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Case {cw.case_id}</CardTitle>
            <div className="flex flex-wrap gap-2 mt-2">
              <Badge>Stage: {cw.current_stage ?? "—"}</Badge>
              <Badge variant="outline">{cw.status}</Badge>
            </div>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-2">
            <p>Progress: {(cw.progress * 100).toFixed(0)}%</p>
            <p>Validation payload is stored on the case for gated advances.</p>
          </CardContent>
        </Card>
      )}

      {last && (
        <Card className={last.blocked ? "border-warning/50 bg-warning/5" : "border-success/40 bg-success/5"}>
          <CardHeader>
            <CardTitle className="text-lg">{last.blocked ? "Blocked" : "Advanced"}</CardTitle>
            <CardDescription>
              {last.blocked
                ? "Rule engine reported violations — complete documentation before advancing."
                : "Current stage completed; case moved to the next pending step."}
            </CardDescription>
          </CardHeader>
        </Card>
      )}
    </div>
  );
}
