import { useCallback, useEffect, useState } from "react";
import { Loader2, RefreshCw, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api, type RejectionPatternsResponse } from "@/lib/api";

export default function Rejections() {
  const [data, setData] = useState<RejectionPatternsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await api.rejectionPatterns();
      setData(r);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto space-y-8">
      <div className="flex flex-wrap justify-between gap-4 items-start">
        <div>
          <h1 className="font-serif text-2xl leading-tight tracking-tight flex items-center gap-2">
            <TriangleAlert className="h-6 w-6" />
            Rejection patterns
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            GET <code className="text-xs">/api/analytics/rejection-patterns</code> — cluster outcomes by jurisdiction and coverage.
          </p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={refresh} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-muted-foreground text-sm">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading…
        </div>
      )}
      {error && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {data && (
        <div className="grid gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Rule coverage (approximate)</CardTitle>
              <CardDescription>From recorded outcome coverage tags.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-4 text-sm">
              {Object.entries(data.rule_coverage_report).map(([k, v]) => (
                <div key={k} className="rounded-lg border border-border px-3 py-2">
                  <div className="text-muted-foreground">{k}</div>
                  <div className="text-lg font-semibold">{typeof v === "number" ? `${v}%` : v}</div>
                </div>
              ))}
              {Object.keys(data.rule_coverage_report).length === 0 && (
                <span className="text-muted-foreground">No outcomes yet.</span>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">By state × category × coverage</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>State</TableHead>
                    <TableHead>Tax category</TableHead>
                    <TableHead>Coverage</TableHead>
                    <TableHead className="text-right">Count</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.by_state.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={4} className="text-muted-foreground">
                        No clustered rows.
                      </TableCell>
                    </TableRow>
                  ) : (
                    data.by_state.map((r, i) => (
                      <TableRow key={`${r.state}-${r.tax_category}-${r.coverage_status}-${i}`}>
                        <TableCell>{r.state}</TableCell>
                        <TableCell>{r.tax_category}</TableCell>
                        <TableCell>{r.coverage_status}</TableCell>
                        <TableCell className="text-right">{r.count}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
