import { useCallback, useEffect, useState } from "react";
import {
  BadgeCheck,
  CircleSlash,
  Loader2,
  Radio,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  Webhook as WebhookIcon,
} from "lucide-react";
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
import { Badge } from "@/components/ui/badge";
import { api, getAppRole, type WebhookDeliveryRow, type WebhookHealthOut, type WebhookSubscriptionRow } from "@/lib/api";

export default function WebhooksPage() {
  const [subs, setSubs] = useState<WebhookSubscriptionRow[]>([]);
  const [deliveries, setDeliveries] = useState<WebhookDeliveryRow[]>([]);
  const [health, setHealth] = useState<WebhookHealthOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [role, setRole] = useState(() => getAppRole());

  const refresh = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const [s, d, h] = await Promise.all([
        api.webhookSubscriptions(false),
        api.webhookDeliveries({ limit: 100 }),
        api.webhookHealth(),
      ]);
      setSubs(s);
      setDeliveries(d.deliveries ?? []);
      setHealth(h);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    const sync = () => setRole(getAppRole());
    window.addEventListener("rules_intel_app_role", sync);
    return () => window.removeEventListener("rules_intel_app_role", sync);
  }, []);

  function statusBadge(status: string, attempt: number) {
    if (status === "success")
      return (
        <Badge className="bg-emerald-600/90 hover:bg-emerald-600">{status}</Badge>
      );
    if (status === "failed")
      return <Badge variant="destructive">{status}</Badge>;
    if (status === "pending" && attempt > 1)
      return <Badge variant="secondary">retrying ({attempt})</Badge>;
    return <Badge variant="outline">{status}</Badge>;
  }

  const canResend = role === "admin";

  async function onResend(deliveryId: string) {
    if (!canResend) return;
    setBusy(true);
    setError(null);
    try {
      await api.webhookResendDelivery(deliveryId);
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto space-y-8">
      <div className="flex flex-wrap justify-between gap-4 items-start">
        <div>
          <h1 className="font-serif text-2xl leading-tight tracking-tight flex items-center gap-2">
            <WebhookIcon className="h-6 w-6" />
            Webhooks
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Subscriptions and delivery attempts (POST payloads run after the API responds).
          </p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={refresh} disabled={busy}>
          <RefreshCw className={`h-4 w-4 mr-2 ${busy ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {health && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
                <Radio className="h-4 w-4" /> Active subscriptions
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold">
                {health.active_subscriptions} / {health.total_subscriptions}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
                <WebhookIcon className="h-4 w-4" /> Deliveries (24h)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold">{health.deliveries_last_24h}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
                <BadgeCheck className="h-4 w-4" /> Success rate (24h)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold">{Math.round(health.success_rate_last_24h * 100)}%</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
                <ShieldAlert className="h-4 w-4" /> Failed (24h)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold">{health.failed_last_24h}</p>
            </CardContent>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Radio className="h-5 w-5" />
            Endpoints
          </CardTitle>
          <CardDescription>
            Register via <code className="text-xs">POST /api/webhooks/register</code> — signing secret is
            returned once.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {busy && subs.length === 0 ? (
            <p className="text-sm text-muted-foreground flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading…
            </p>
          ) : subs.length === 0 ? (
            <p className="text-sm text-muted-foreground">No subscriptions yet.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>URL</TableHead>
                  <TableHead>Events</TableHead>
                  <TableHead>Hint</TableHead>
                  <TableHead>Active</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {subs.map((s) => (
                  <TableRow key={s.id}>
                    <TableCell className="max-w-[240px] truncate font-mono text-xs">{s.url}</TableCell>
                    <TableCell className="text-xs">{(s.events || []).join(", ") || "all"}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{s.secret_hint ?? "—"}</TableCell>
                    <TableCell>
                      {s.active ? (
                        <BadgeCheck className="h-4 w-4 text-emerald-500" />
                      ) : (
                        <span className="text-muted-foreground">off</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Delivery attempts</CardTitle>
          <CardDescription>
            <code className="text-xs">GET /api/webhooks/deliveries</code>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Event</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Attempts</TableHead>
                <TableHead>HTTP</TableHead>
                <TableHead>Error</TableHead>
                <TableHead>Resend</TableHead>
                <TableHead>Time</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {deliveries.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-muted-foreground text-sm">
                    No deliveries recorded.
                  </TableCell>
                </TableRow>
              ) : (
                deliveries.map((d) => (
                  <TableRow key={d.id}>
                    <TableCell className="font-mono text-xs">{d.event_type}</TableCell>
                    <TableCell>{statusBadge(d.status, d.attempt_count)}</TableCell>
                    <TableCell>{d.attempt_count}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {d.response_status_code ?? "—"}
                      {d.duration_ms != null ? ` · ${d.duration_ms}ms` : ""}
                    </TableCell>
                    <TableCell className="max-w-[200px] truncate text-xs text-destructive">
                      {d.last_error ?? "—"}
                    </TableCell>
                    <TableCell>
                      {d.status === "failed" ? (
                        <Button
                          type="button"
                          size="sm"
                          variant={canResend ? "outline" : "secondary"}
                          disabled={!canResend || busy}
                          onClick={() => void onResend(d.id)}
                        >
                          {canResend ? <RotateCcw className="h-3.5 w-3.5 mr-1.5" /> : <CircleSlash className="h-3.5 w-3.5 mr-1.5" />}
                          Resend
                        </Button>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                      {new Date(d.created_at).toLocaleString()}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
