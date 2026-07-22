import { Link } from "react-router-dom";
import { Plus, FileText, CheckCircle2, XCircle, FlaskConical } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/domain/EmptyState";
import { useHealth, useHistory } from "@/lib/queries";
import { formatDate } from "@/lib/utils";

function HealthRow({
  label,
  ok,
  detail,
}: {
  label: string;
  ok: boolean;
  detail?: string;
}) {
  return (
    <div className="flex items-center justify-between rounded-md border border-border/60 px-3 py-2 text-sm">
      <div className="flex items-center gap-2">
        {ok ? (
          <CheckCircle2 className="h-4 w-4 text-success" />
        ) : (
          <XCircle className="h-4 w-4 text-destructive" />
        )}
        <span className="font-medium">{label}</span>
      </div>
      {detail && (
        <span className="text-xs text-muted-foreground">{detail}</span>
      )}
    </div>
  );
}

export function Dashboard() {
  const { data: health, isLoading: healthLoading } = useHealth();
  const { data: history, isLoading: historyLoading } = useHistory();

  const lastRuns = (history ?? []).slice(0, 5);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Panoramica sistema e ultimi run
          </p>
        </div>
        <Button asChild size="lg">
          <Link to="/new">
            <Plus className="h-4 w-4" />
            Nuovo run
          </Link>
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Health */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Stato sistema</CardTitle>
            <CardDescription>
              Controlli di connettivita' e credenziali
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {healthLoading ? (
              <>
                <Skeleton className="h-9 w-full" />
                <Skeleton className="h-9 w-full" />
                <Skeleton className="h-9 w-full" />
                <Skeleton className="h-9 w-full" />
              </>
            ) : health ? (
              <>
                <HealthRow
                  label="Fatture in Cloud"
                  ok={health.fic_token_valid}
                  detail={health.company?.name ?? undefined}
                />
                <HealthRow label="Database" ok={health.db_ok} />
                <HealthRow
                  label="Gmail personale"
                  ok={!!health.gmail_tokens_ok?.personal}
                />
                <HealthRow
                  label="Gmail business"
                  ok={!!health.gmail_tokens_ok?.business}
                />
                <HealthRow
                  label="Anthropic API"
                  ok={health.anthropic_api_ok}
                />
              </>
            ) : (
              <div className="text-sm text-muted-foreground">
                Impossibile caricare lo stato.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Last runs */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Ultimi 5 run</CardTitle>
            <CardDescription>
              Storico delle esecuzioni piu' recenti
            </CardDescription>
          </CardHeader>
          <CardContent>
            {historyLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-9 w-full" />
                <Skeleton className="h-9 w-full" />
                <Skeleton className="h-9 w-full" />
              </div>
            ) : lastRuns.length === 0 ? (
              <EmptyState
                icon={FileText}
                title="Nessun run ancora"
                description="Carica un estratto conto per iniziare il primo run."
                action={
                  <Button asChild size="sm">
                    <Link to="/new">Nuovo run</Link>
                  </Button>
                }
              />
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Data</TableHead>
                      <TableHead>Statement</TableHead>
                      <TableHead className="text-right">Tot.</TableHead>
                      <TableHead className="text-right">Ok</TableHead>
                      <TableHead className="text-right">Errori</TableHead>
                      <TableHead>Tipo</TableHead>
                      <TableHead></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {lastRuns.map((r) => (
                      <TableRow key={r.id}>
                        <TableCell className="text-xs">
                          {formatDate(r.started_at, "short")}
                        </TableCell>
                        <TableCell className="max-w-[180px] truncate text-xs font-mono">
                          {r.statement_id || "—"}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {r.total_count}
                        </TableCell>
                        <TableCell className="text-right tabular-nums text-success">
                          {r.created_count}
                        </TableCell>
                        <TableCell className="text-right tabular-nums text-destructive">
                          {r.error_count}
                        </TableCell>
                        <TableCell>
                          {r.dry_run ? (
                            <Badge variant="amber" className="gap-1">
                              <FlaskConical className="h-3 w-3" />
                              Dry
                            </Badge>
                          ) : (
                            <Badge variant="success">Live</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <Button
                            asChild
                            size="sm"
                            variant="ghost"
                          >
                            <Link to={`/history/${r.id}`}>Dettagli</Link>
                          </Button>
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
    </div>
  );
}
