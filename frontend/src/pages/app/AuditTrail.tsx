import { useCallback, useEffect, useRef, useState } from "react";
import { AlertCircle, Loader2, RefreshCw, ScrollText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AuditLogPublic,
  ApiError,
  getApiRoleHeader,
  getAuditLogs,
} from "@/lib/api";

function detailSummary(d: Record<string, unknown> | null): string {
  if (!d || !Object.keys(d).length) return "—";
  const s = JSON.stringify(d);
  if (s.length <= 240) return s;
  return `${s.slice(0, 237)}…`;
}

export default function AuditTrail() {
  const [roleBlocked, setRoleBlocked] = useState(() => getApiRoleHeader() === "viewer");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<AuditLogPublic[]>([]);
  const [total, setTotal] = useState(0);
  const [entityType, setEntityType] = useState("");
  const [action, setAction] = useState("");
  const [actor, setActor] = useState("");
  const filtersRef = useRef({ entityType, action, actor });
  filtersRef.current = { entityType, action, actor };

  const load = useCallback(async () => {
    if (getApiRoleHeader() === "viewer") {
      setRoleBlocked(true);
      setLogs([]);
      setTotal(0);
      return;
    }
    setRoleBlocked(false);
    setLoading(true);
    setError(null);
    const f = filtersRef.current;
    try {
      const data = await getAuditLogs({
        entity_type: f.entityType.trim() || undefined,
        action: f.action.trim() || undefined,
        actor: f.actor.trim() || undefined,
        limit: 100,
        offset: 0,
      });
      setLogs(data.logs);
      setTotal(data.total);
    } catch (e: unknown) {
      if (e instanceof ApiError && e.status === 403) {
        setError("Audit trail requires reviewer or admin access.");
      } else {
        setError(e instanceof Error ? e.message : String(e));
      }
      setLogs([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const onRole = () => void load();
    window.addEventListener("rules_intel_app_role", onRole);
    return () => window.removeEventListener("rules_intel_app_role", onRole);
  }, [load]);

  if (roleBlocked) {
    return (
      <div className="p-6 lg:p-8 max-w-[960px]">
        <p className="text-xs uppercase tracking-widest text-muted-foreground">Governance</p>
        <h1 className="text-3xl font-bold tracking-tight mt-1 flex items-center gap-2">
          <ScrollText className="h-7 w-7 text-muted-foreground" />
          Audit Trail
        </h1>
        <p className="text-sm text-muted-foreground mt-2 border border-border/60 rounded-lg px-4 py-3 bg-secondary/25">
          Audit trail requires reviewer or admin access.
        </p>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-[1400px]">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-widest text-muted-foreground">Governance</p>
          <h1 className="text-3xl font-bold tracking-tight mt-1 flex items-center gap-2">
            <ScrollText className="h-7 w-7 text-primary" />
            Audit Trail
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Important append-only actions from the governed audit log ({total.toLocaleString()} matching).
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-3 rounded-xl border border-border/70 bg-secondary/15 p-4">
        <div className="space-y-1.5">
          <Label htmlFor="audit-et" className="text-xs text-muted-foreground">
            Entity type
          </Label>
          <Input
            id="audit-et"
            placeholder="e.g. submission, ingestion_run"
            value={entityType}
            onChange={(e) => setEntityType(e.target.value)}
            className="h-9"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="audit-action" className="text-xs text-muted-foreground">
            Action
          </Label>
          <Input
            id="audit-action"
            placeholder="e.g. validate_submission"
            value={action}
            onChange={(e) => setAction(e.target.value)}
            className="h-9"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="audit-actor" className="text-xs text-muted-foreground">
            Actor
          </Label>
          <Input
            id="audit-actor"
            placeholder="user id substring"
            value={actor}
            onChange={(e) => setActor(e.target.value)}
            className="h-9"
          />
        </div>
      </div>
      <p className="text-xs text-muted-foreground">
        Set filters, then use Refresh to query the server.
      </p>

      {error && (
        <div className="rounded-xl border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm flex items-start gap-2">
          <AlertCircle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      <div className="rounded-xl border border-border/70 overflow-hidden bg-background/80">
        {loading ? (
          <div className="flex items-center justify-center py-24 text-muted-foreground gap-2">
            <Loader2 className="h-5 w-5 animate-spin" />
            Loading audit entries…
          </div>
        ) : logs.length === 0 ? (
          <div className="py-16 text-center text-sm text-muted-foreground">No audit entries yet.</div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[155px]">Time</TableHead>
                <TableHead>Actor</TableHead>
                <TableHead className="w-[90px]">Role</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Entity</TableHead>
                <TableHead>ID</TableHead>
                <TableHead className="min-w-[200px]">Details</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {logs.map((row) => (
                <TableRow key={row.id}>
                  <TableCell className="text-xs whitespace-nowrap font-mono text-muted-foreground">
                    {new Date(row.created_at).toLocaleString()}
                  </TableCell>
                  <TableCell className="text-sm">{row.actor ?? "—"}</TableCell>
                  <TableCell className="text-xs capitalize">{row.user_role ?? "—"}</TableCell>
                  <TableCell className="text-sm font-medium">{row.action}</TableCell>
                  <TableCell className="text-xs">{row.entity_type}</TableCell>
                  <TableCell className="text-xs font-mono max-w-[120px] truncate" title={row.entity_id ?? ""}>
                    {row.entity_id ?? "—"}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground max-w-xl break-all">
                    {detailSummary(row.detail)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  );
}
