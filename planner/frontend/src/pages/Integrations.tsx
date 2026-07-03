import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  Activity,
  CheckCircle2,
  KeyRound,
  Loader2,
  Plug,
  RefreshCw,
  Unlink,
  Users,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/domain/EmptyState";
import {
  useDisconnectKlaviyo,
  useKlaviyoInsights,
  useKlaviyoStatus,
  useSaveKlaviyoKey,
  useSyncKlaviyo,
  useSystemStatus,
} from "@/lib/queries";
import { ApiError } from "@/lib/api";
import { cn, formatCurrency, formatDate, formatPercent } from "@/lib/utils";
import type { EngagementHealth } from "@/types/api";

const HEALTH_CONFIG: Record<
  EngagementHealth,
  { label: string; className: string; dot: string }
> = {
  good: {
    label: "Buona",
    className: "text-emerald-700",
    dot: "bg-emerald-500",
  },
  average: {
    label: "Media",
    className: "text-amber-700",
    dot: "bg-amber-500",
  },
  poor: { label: "Scarsa", className: "text-red-700", dot: "bg-red-500" },
  unknown: {
    label: "Sconosciuta",
    className: "text-muted-foreground",
    dot: "bg-zinc-400",
  },
};

function Metric({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border/60 bg-muted/30 px-4 py-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 text-lg font-semibold tabular-nums">{value}</div>
    </div>
  );
}

export function Integrations() {
  const { brandId: brandIdParam } = useParams();
  const brandId = Number(brandIdParam);

  const { data: status, isLoading: statusLoading } = useKlaviyoStatus(brandId);
  const { data: system } = useSystemStatus();
  const insights = useKlaviyoInsights(brandId);
  const saveKey = useSaveKlaviyoKey(brandId);
  const disconnect = useDisconnectKlaviyo(brandId);
  const sync = useSyncKlaviyo(brandId);

  const [apiKey, setApiKey] = useState("");

  const neverSynced =
    insights.isError &&
    insights.error instanceof ApiError &&
    insights.error.status === 404;

  function handleSaveKey() {
    if (!apiKey.trim()) {
      toast.error("Inserisci una API key Klaviyo");
      return;
    }
    saveKey.mutate(apiKey.trim(), {
      onSuccess: () => {
        toast.success("API key salvata");
        setApiKey("");
      },
      onError: (err) => toast.error(`Errore: ${err.message}`),
    });
  }

  function handleSync() {
    sync.mutate(undefined, {
      onSuccess: (snapshot) => {
        toast.success(
          `Sincronizzazione completata: ${snapshot.segments.length} segmenti, ${snapshot.campaigns.length} campagne`
        );
      },
      onError: (err) => {
        if (err.status === 502) {
          toast.error(`Klaviyo non raggiungibile o chiave non valida: ${err.message}`);
        } else {
          toast.error(`Errore sincronizzazione: ${err.message}`);
        }
      },
    });
  }

  // In modalità demo la sync funziona anche senza chiave (dati finti)
  const canSync = Boolean(status?.configured || system?.mock_mode);

  const snapshot = insights.data;
  const health = snapshot
    ? HEALTH_CONFIG[snapshot.metrics_summary.engagement_health]
    : null;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">Integrazioni</h1>
        <p className="text-sm text-muted-foreground">
          Collega le fonti dati del brand.
        </p>
      </div>

      {/* Card Klaviyo */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Plug className="h-4 w-4" />
                Klaviyo
              </CardTitle>
              <CardDescription>
                Segmenti, campagne e metriche per informare la generazione dei
                piani.
              </CardDescription>
            </div>
            {statusLoading ? (
              <Skeleton className="h-6 w-24" />
            ) : status?.configured ? (
              <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Collegato
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 rounded-full border border-border bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">
                <XCircle className="h-3.5 w-3.5" />
                Non collegato
              </span>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {status?.configured && (
            <div className="flex flex-wrap items-center gap-x-6 gap-y-1 text-sm text-muted-foreground">
              {status.account_name && (
                <span>
                  Account:{" "}
                  <span className="font-medium text-foreground">
                    {status.account_name}
                  </span>
                </span>
              )}
              {status.key_preview && <span>Chiave: {status.key_preview}</span>}
              <span>
                Ultima sincronizzazione:{" "}
                {status.last_sync_at
                  ? formatDate(status.last_sync_at, "long")
                  : "mai"}
              </span>
            </div>
          )}

          {status?.error && (
            <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {status.error}
            </p>
          )}

          <div className="flex flex-wrap items-end gap-2">
            <div className="min-w-[260px] flex-1 space-y-2">
              <Label htmlFor="klaviyo-key">
                {status?.configured ? "Sostituisci API key" : "API key privata"}
              </Label>
              <Input
                id="klaviyo-key"
                type="password"
                placeholder="pk_…"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
            </div>
            <Button
              onClick={handleSaveKey}
              disabled={saveKey.isPending}
              variant="outline"
            >
              <KeyRound className="h-4 w-4" />
              {saveKey.isPending ? "Salvataggio…" : "Salva chiave"}
            </Button>
            {canSync && (
              <>
                <Button onClick={handleSync} disabled={sync.isPending}>
                  {sync.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <RefreshCw className="h-4 w-4" />
                  )}
                  {sync.isPending ? "Sincronizzazione…" : "Sincronizza dati"}
                </Button>
                {status?.configured && (
                <Button
                  variant="ghost"
                  onClick={() => {
                    if (window.confirm("Scollegare Klaviyo da questo brand?")) {
                      disconnect.mutate(undefined, {
                        onSuccess: () => toast.success("Klaviyo scollegato"),
                        onError: (err) => toast.error(`Errore: ${err.message}`),
                      });
                    }
                  }}
                >
                  <Unlink className="h-4 w-4" />
                  Scollega
                </Button>
                )}
              </>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Insights */}
      {canSync && (
        <>
          {insights.isLoading ? (
            <Skeleton className="h-64 w-full" />
          ) : neverSynced || !snapshot ? (
            <EmptyState
              icon={Activity}
              title="Nessun dato sincronizzato"
              description='Premi "Sincronizza dati" per importare segmenti, campagne e metriche da Klaviyo.'
              action={
                <Button onClick={handleSync} disabled={sync.isPending}>
                  {sync.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <RefreshCw className="h-4 w-4" />
                  )}
                  Sincronizza dati
                </Button>
              }
            />
          ) : (
            <>
              {/* Metriche */}
              <Card>
                <CardHeader>
                  <CardTitle>Riepilogo metriche</CardTitle>
                  <CardDescription>
                    Snapshot del {formatDate(snapshot.synced_at, "long")}
                    {snapshot.account_name ? ` · ${snapshot.account_name}` : ""}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                    <Metric
                      label="Profili totali"
                      value={
                        snapshot.total_profiles != null
                          ? snapshot.total_profiles.toLocaleString("it-IT")
                          : "—"
                      }
                    />
                    <Metric
                      label="Open rate medio"
                      value={formatPercent(
                        snapshot.metrics_summary.avg_open_rate
                      )}
                    />
                    <Metric
                      label="Click rate medio"
                      value={formatPercent(
                        snapshot.metrics_summary.avg_click_rate
                      )}
                    />
                    <Metric
                      label="Revenue 30gg"
                      value={formatCurrency(
                        snapshot.metrics_summary.total_revenue_30d
                      )}
                    />
                    <Metric
                      label="Salute engagement"
                      value={
                        health && (
                          <span
                            className={cn(
                              "inline-flex items-center gap-1.5 text-base",
                              health.className
                            )}
                          >
                            <span
                              className={cn(
                                "h-2.5 w-2.5 rounded-full",
                                health.dot
                              )}
                            />
                            {health.label}
                          </span>
                        )
                      }
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Segmenti */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Users className="h-4 w-4" />
                    Segmenti
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {snapshot.segments.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      Nessun segmento trovato.
                    </p>
                  ) : (
                    <ul className="divide-y divide-border/60">
                      {snapshot.segments.map((segment) => (
                        <li
                          key={segment.klaviyo_id}
                          className="flex items-center justify-between py-2 text-sm"
                        >
                          <span className="font-medium">{segment.name}</span>
                          <span className="tabular-nums text-muted-foreground">
                            {segment.profile_count != null
                              ? `${segment.profile_count.toLocaleString("it-IT")} profili`
                              : "—"}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </CardContent>
              </Card>

              {/* Campagne */}
              <Card>
                <CardHeader>
                  <CardTitle>Ultime campagne</CardTitle>
                </CardHeader>
                <CardContent>
                  {snapshot.campaigns.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      Nessuna campagna trovata.
                    </p>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Campagna</TableHead>
                          <TableHead>Inviata</TableHead>
                          <TableHead className="text-right">
                            Destinatari
                          </TableHead>
                          <TableHead className="text-right">Open</TableHead>
                          <TableHead className="text-right">Click</TableHead>
                          <TableHead className="text-right">Revenue</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {snapshot.campaigns.map((campaign) => (
                          <TableRow key={campaign.klaviyo_id}>
                            <TableCell className="max-w-[220px] truncate font-medium">
                              {campaign.name}
                            </TableCell>
                            <TableCell className="text-muted-foreground">
                              {formatDate(campaign.sent_at)}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                              {campaign.recipients != null
                                ? campaign.recipients.toLocaleString("it-IT")
                                : "—"}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                              {formatPercent(campaign.open_rate)}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                              {formatPercent(campaign.click_rate)}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                              {formatCurrency(campaign.revenue)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </CardContent>
              </Card>

              {/* Raccomandazioni */}
              {snapshot.recommendations.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Raccomandazioni</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {snapshot.recommendations.map((rec, i) => (
                        <li
                          key={i}
                          className="flex items-start gap-2 text-sm"
                        >
                          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                          {rec}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
