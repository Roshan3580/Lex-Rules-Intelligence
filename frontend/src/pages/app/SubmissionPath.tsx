import { useState } from "react";
import { ExternalLink, Loader2, Route as RouteIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api, type SubmissionPathResponse } from "@/lib/api";

export default function SubmissionPath() {
  const [state, setState] = useState("California");
  const [taxCategory, setTaxCategory] = useState("sales_tax");
  const [stage, setStage] = useState("submission");
  const [txn, setTxn] = useState("");
  const [busy, setBusy] = useState(false);
  const [data, setData] = useState<SubmissionPathResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setBusy(true);
    setError(null);
    try {
      const res = await api.submissionPath({
        state,
        tax_category: taxCategory,
        workflow_stage: stage || undefined,
        transaction_type: txn || undefined,
      });
      setData(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      setData(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="p-6 lg:p-8 max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
          <RouteIcon className="h-6 w-6" />
          Submission path
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          GET <code className="text-xs">/api/submission-path</code> — portal steps and document checklist from published rules (no LLM).
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Filters</CardTitle>
          <CardDescription>State / tax category match the rule index.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label>State</Label>
            <Input value={state} onChange={(e) => setState(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Tax category</Label>
            <Input value={taxCategory} onChange={(e) => setTaxCategory(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Workflow stage</Label>
            <Input value={stage} onChange={(e) => setStage(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Transaction type (optional)</Label>
            <Input value={txn} onChange={(e) => setTxn(e.target.value)} placeholder="retail, B2B…" />
          </div>
          <div className="sm:col-span-2">
            <Button type="button" onClick={load} disabled={busy}>
              {busy && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Load path
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {data && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Recommended</CardTitle>
              <div className="flex flex-wrap gap-2 mt-2">
                <Badge>{data.recommended_path}</Badge>
                {data.submission_methods.map((m) => (
                  <Badge key={m} variant="outline">
                    {m}
                  </Badge>
                ))}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h3 className="text-sm font-medium mb-2">Steps</h3>
                <ol className="list-decimal pl-5 space-y-1 text-sm text-muted-foreground">
                  {data.steps.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ol>
              </div>
              {data.portal_urls && data.portal_urls.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium mb-2">Portal / source links</h3>
                  <ul className="space-y-1">
                    {data.portal_urls.map((u) => (
                      <li key={u}>
                        <a
                          href={u.startsWith("http") ? u : `https://${u}`}
                          className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
                          target="_blank"
                          rel="noreferrer"
                        >
                          {u.slice(0, 80)}
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div>
                <h3 className="text-sm font-medium mb-2">Required documents / forms</h3>
                <div className="flex flex-wrap gap-2">
                  {data.required_documents.length === 0 ? (
                    <span className="text-sm text-muted-foreground">None inferred from rules.</span>
                  ) : (
                    data.required_documents.map((d) => (
                      <Badge key={d} variant="secondary">
                        {d}
                      </Badge>
                    ))
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
