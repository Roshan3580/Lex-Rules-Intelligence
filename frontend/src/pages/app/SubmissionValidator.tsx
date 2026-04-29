import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  CheckCircle2,
  ExternalLink,
  Loader2,
  XCircle,
  AlertTriangle,
  FlaskConical,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import {
  api,
  confidenceToPct,
  type ValidateSubmissionResponse,
} from "@/lib/api";

const defaultEffectiveDate = "2026-04-28";

/** Baseline form values — different from `loadRiskyCa` so the preset visibly changes fields. */
const INITIAL_BASELINE = {
  state: "NY",
  taxCategory: "withholding",
  workflowStage: "intake",
  effectiveDate: defaultEffectiveDate,
  amount: "1200",
  entityType: "C-Corp",
  submissionMethod: "mail",
  documentsCsv: "Form IT-2104",
} as const;

export default function SubmissionValidator() {
  const [state, setState] = useState(INITIAL_BASELINE.state);
  const [taxCategory, setTaxCategory] = useState(INITIAL_BASELINE.taxCategory);
  const [workflowStage, setWorkflowStage] = useState(INITIAL_BASELINE.workflowStage);
  const [effectiveDate, setEffectiveDate] = useState(INITIAL_BASELINE.effectiveDate);
  const [amount, setAmount] = useState(INITIAL_BASELINE.amount);
  const [entityType, setEntityType] = useState(INITIAL_BASELINE.entityType);
  const [submissionMethod, setSubmissionMethod] = useState(INITIAL_BASELINE.submissionMethod);
  const [documentsCsv, setDocumentsCsv] = useState(INITIAL_BASELINE.documentsCsv);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ValidateSubmissionResponse | null>(null);

  const payload = useMemo(() => {
    const docs = documentsCsv
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    return {
      documents: docs,
      amount: amount === "" ? undefined : Number(amount),
      entity_type: entityType || undefined,
      submission_method: submissionMethod || undefined,
    };
  }, [amount, documentsCsv, entityType, submissionMethod]);

  async function validate() {
    setBusy(true);
    setError(null);
    try {
      const res = await api.validateSubmission({
        state,
        tax_category: taxCategory,
        workflow_stage: workflowStage || undefined,
        effective_date: effectiveDate || undefined,
        payload,
      });
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      setResult(null);
    } finally {
      setBusy(false);
    }
  }

  function loadRiskyCa() {
    setState("CA");
    setTaxCategory("sales_tax");
    setWorkflowStage("submission");
    setEffectiveDate(defaultEffectiveDate);
    setAmount("50000");
    setEntityType("LLC");
    setSubmissionMethod("portal");
    setDocumentsCsv("Form A");
    setResult(null);
    setError(null);
    toast.success("Loaded risky CA sample", {
      description: "California · sales tax · submission · LLC · $50k · docs: Form A only. Run Validate to see blocks.",
    });
  }

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Submission Validator</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Deterministic pre-submission check against published and approved rules — no LLM on this path.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Submission details</CardTitle>
          <CardDescription>
            Maps to <code className="text-xs">POST /api/validate-submission</code> — payload fields are merged into the request body.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="state">State</Label>
            <Input
              id="state"
              value={state}
              onChange={(e) => setState(e.target.value)}
              placeholder="CA or California"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="tax">Tax category</Label>
            <Input
              id="tax"
              value={taxCategory}
              onChange={(e) => setTaxCategory(e.target.value)}
              placeholder="sales_tax"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="stage">Workflow stage</Label>
            <Input
              id="stage"
              value={workflowStage}
              onChange={(e) => setWorkflowStage(e.target.value)}
              placeholder="submission"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="eff">Effective date</Label>
            <Input
              id="eff"
              type="date"
              value={effectiveDate}
              onChange={(e) => setEffectiveDate(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="amt">Amount</Label>
            <Input
              id="amt"
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="entity">Entity type</Label>
            <Input
              id="entity"
              value={entityType}
              onChange={(e) => setEntityType(e.target.value)}
              placeholder="LLC"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="meth">Submission method</Label>
            <Input
              id="meth"
              value={submissionMethod}
              onChange={(e) => setSubmissionMethod(e.target.value)}
              placeholder="portal"
            />
          </div>
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="docs">Documents / forms (comma-separated)</Label>
            <Input
              id="docs"
              value={documentsCsv}
              onChange={(e) => setDocumentsCsv(e.target.value)}
              placeholder="Form A, CDTFA-401-A"
            />
          </div>
          <div className="sm:col-span-2 flex flex-wrap gap-3">
            <Button type="button" onClick={validate} disabled={busy}>
              {busy && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Validate submission
            </Button>
            <Button type="button" variant="outline" onClick={loadRiskyCa}>
              <FlaskConical className="h-4 w-4 mr-2" />
              Load risky CA submission
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {result && (
        <Card
          className={
            result.valid
              ? "border-success/40 bg-success/5"
              : "border-destructive/40 bg-destructive/5"
          }
        >
          <CardHeader className="flex flex-row items-start gap-4 space-y-0">
            {result.valid ? (
              <CheckCircle2 className="h-8 w-8 text-success shrink-0" />
            ) : (
              <XCircle className="h-8 w-8 text-destructive shrink-0" />
            )}
            <div>
              <CardTitle className="text-lg">
                {result.valid ? "Submission cleared" : "Submission blocked"}
              </CardTitle>
              <CardDescription className="mt-1">{result.explanation}</CardDescription>
              <div className="mt-2 flex flex-wrap gap-2">
                <Badge variant="outline">Risk: {result.risk_level}</Badge>
                {!result.valid && (
                  <Badge variant="destructive">{result.violations.length} violation(s)</Badge>
                )}
              </div>
            </div>
          </CardHeader>
          {result.warnings.length > 0 && (
            <CardContent className="pt-0">
              <div className="flex gap-2 text-sm text-warning">
                <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                <ul className="list-disc pl-4 space-y-1">
                  {result.warnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              </div>
            </CardContent>
          )}
        </Card>
      )}

      {result && result.violations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Violations</CardTitle>
            <CardDescription>Each item ties back to a stored rule and source snippet.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {result.violations.map((v) => (
              <div
                key={v.rule_id}
                className="rounded-xl border border-border/80 bg-card/50 p-4 space-y-2"
              >
                <div className="flex flex-wrap items-center gap-2 justify-between">
                  <h3 className="font-medium">{v.rule_title}</h3>
                  <Badge variant="secondary">{confidenceToPct(v.confidence)}% confidence</Badge>
                </div>
                <p className="text-sm text-muted-foreground">{v.reason}</p>
                <p className="text-sm">
                  <span className="font-medium text-foreground">Required action: </span>
                  {v.required_action}
                </p>
                {v.required_documentation?.length > 0 && (
                  <p className="text-sm text-muted-foreground">
                    Missing docs/forms: {v.required_documentation.join(", ")}
                  </p>
                )}
                {v.source?.snippet && (
                  <blockquote className="text-xs border-l-2 border-primary/40 pl-3 py-1 text-muted-foreground italic">
                    {v.source.snippet}
                  </blockquote>
                )}
                {v.source?.source_url && (
                  <a
                    href={v.source.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                  >
                    Source evidence <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Why this matters</CardTitle>
        </CardHeader>
        <CardContent className="prose prose-sm dark:prose-invert max-w-none text-muted-foreground space-y-2">
          <p>
            <strong className="text-foreground">Prevents rejections before submission</strong> by matching your payload against the same published rules operators rely on in review — with explicit reasons, not free‑text guesses.
          </p>
          <p>
            <strong className="text-foreground">Explains the blocking rule</strong> (title, required action, missing artifacts) and links to the underlying source URL and stored snippet where available.
          </p>
          <p>
            Outcomes logged on the{" "}
            <Link to="/app/outcomes" className="text-primary hover:underline">
              Outcomes
            </Link>{" "}
            page close the loop: you can see whether a rejection was already covered by the rule base.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
