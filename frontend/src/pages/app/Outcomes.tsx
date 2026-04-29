import { useCallback, useEffect, useState } from "react";
import { Loader2, RefreshCw } from "lucide-react";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  api,
  type OutcomeEvent,
  type RejectionCoverageResponse,
} from "@/lib/api";

function coverageVariant(
  s: string,
): "default" | "secondary" | "destructive" | "outline" {
  switch (s) {
    case "prevented_by_existing_rule":
      return "default";
    case "rule_existed_but_not_enforced":
      return "secondary";
    case "missing_rule":
      return "destructive";
    default:
      return "outline";
  }
}

export default function Outcomes() {
  const [list, setList] = useState<OutcomeEvent[]>([]);
  const [coverage, setCoverage] = useState<RejectionCoverageResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitBusy, setSubmitBusy] = useState(false);

  const [submissionId, setSubmissionId] = useState("");
  const [state, setState] = useState("NY");
  const [taxCategory, setTaxCategory] = useState("sales_tax");
  const [workflowStage, setWorkflowStage] = useState("submission");
  const [rejectionCode, setRejectionCode] = useState("R102");
  const [rejectionReason, setRejectionReason] = useState(
    "Missing required documentation for sales tax filing",
  );
  const [documentsCsv, setDocumentsCsv] = useState("Form A");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [rows, cov] = await Promise.all([
        api.listOutcomes({ limit: 50 }),
        api.rejectionCoverage(),
      ]);
      setList(rows);
      setCoverage(cov);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function submitOutcome() {
    setSubmitBusy(true);
    setError(null);
    try {
      const docs = documentsCsv
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      await api.createOutcome({
        submission_id: submissionId || undefined,
        state,
        tax_category: taxCategory,
        workflow_stage: workflowStage || undefined,
        rejection_code: rejectionCode || undefined,
        rejection_reason: rejectionReason,
        payload: { documents: docs, note: "manual outcome entry" },
      });
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitBusy(false);
    }
  }

  const missingRuleCount =
    coverage?.by_coverage_status.find((r) => r.coverage_status === "missing_rule")
      ?.count ?? 0;

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Outcomes & coverage</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Log rejections and compare them to deterministic validation —{" "}
            <code className="text-xs">POST /api/outcomes</code>,{" "}
            <code className="text-xs">GET /api/analytics/rejection-coverage</code>.
          </p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={refresh} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {coverage && (
        <div className="grid gap-4 sm:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total outcomes</CardDescription>
              <CardTitle className="text-3xl tabular-nums">{coverage.total_outcomes}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Missing rule (estimated)</CardDescription>
              <CardTitle className="text-3xl tabular-nums">{missingRuleCount}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Coverage (prevented / total)</CardDescription>
              <CardTitle className="text-3xl tabular-nums">
                {coverage.coverage_percentage}%
              </CardTitle>
            </CardHeader>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Record rejection / outcome</CardTitle>
          <CardDescription>
            Stored for analytics; coverage status is computed against published rules and{" "}
            <code className="text-xs">validate-submission</code>.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="sid">Submission ID (optional)</Label>
            <Input
              id="sid"
              value={submissionId}
              onChange={(e) => setSubmissionId(e.target.value)}
              placeholder="sub_123"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ost">State</Label>
            <Input id="ost" value={state} onChange={(e) => setState(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="otax">Tax category</Label>
            <Input
              id="otax"
              value={taxCategory}
              onChange={(e) => setTaxCategory(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="owf">Workflow stage</Label>
            <Input
              id="owf"
              value={workflowStage}
              onChange={(e) => setWorkflowStage(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ocode">Rejection code</Label>
            <Input
              id="ocode"
              value={rejectionCode}
              onChange={(e) => setRejectionCode(e.target.value)}
            />
          </div>
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="oreas">Rejection reason</Label>
            <Input
              id="oreas"
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
            />
          </div>
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="odocs">Payload documents (comma-separated)</Label>
            <Input
              id="odocs"
              value={documentsCsv}
              onChange={(e) => setDocumentsCsv(e.target.value)}
            />
          </div>
          <div className="sm:col-span-2">
            <Button type="button" onClick={submitOutcome} disabled={submitBusy}>
              {submitBusy && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Submit outcome
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Recent outcomes</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground py-8 justify-center">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading…
            </div>
          ) : list.length === 0 ? (
            <p className="text-sm text-muted-foreground py-6 text-center">No outcomes yet.</p>
          ) : (
            <div className="rounded-md border overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>When</TableHead>
                    <TableHead>State / category</TableHead>
                    <TableHead>Reason</TableHead>
                    <TableHead>Coverage</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {list.map((o) => (
                    <TableRow key={o.id}>
                      <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                        {new Date(o.created_at).toLocaleString()}
                      </TableCell>
                      <TableCell className="text-sm">
                        {o.state}
                        <br />
                        <span className="text-muted-foreground">{o.tax_category}</span>
                      </TableCell>
                      <TableCell className="text-sm max-w-xs truncate" title={o.rejection_reason}>
                        {o.rejection_reason}
                      </TableCell>
                      <TableCell>
                        <Badge variant={coverageVariant(o.coverage_status)}>
                          {o.coverage_status}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
