import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ExternalLink, CheckCircle2, XCircle } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useHistoryDetail } from "@/lib/queries";
import { formatCurrency, formatDate } from "@/lib/utils";

export function HistoryDetail() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading } = useHistoryDetail(id);

  if (isLoading || !data) {
    return (
      <div className="mx-auto max-w-5xl space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  const items = data.result_json ?? [];

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Button asChild variant="ghost" size="sm">
            <Link to="/history">
              <ArrowLeft className="h-4 w-4" />
              Storico
            </Link>
          </Button>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight">
            Run #{data.id}
          </h1>
          <p className="text-sm text-muted-foreground">
            {formatDate(data.started_at, "long")}
            {data.statement_id && (
              <span className="ml-2 font-mono text-xs">
                · {data.statement_id}
              </span>
            )}
          </p>
        </div>
        {data.dry_run ? (
          <Badge variant="amber">Dry-run</Badge>
        ) : (
          <Badge variant="success">Live</Badge>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">Totale</div>
            <div className="text-2xl font-semibold tabular-nums">
              {data.total_count}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">Create</div>
            <div className="text-2xl font-semibold tabular-nums text-success">
              {data.created_count}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">Errori</div>
            <div className="text-2xl font-semibold tabular-nums text-destructive">
              {data.error_count}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">Saltate</div>
            <div className="text-2xl font-semibold tabular-nums">
              {data.skipped_count}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Dettaglio autofatture</CardTitle>
          <CardDescription>
            Autofatture create/tentate in questo run
          </CardDescription>
        </CardHeader>
        <CardContent>
          {items.length === 0 ? (
            <div className="py-6 text-center text-sm text-muted-foreground">
              Nessun item.
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {items.map((item, i) => (
                <Card
                  key={i}
                  className={
                    item.status === "ok"
                      ? "border-success/30 bg-success/5"
                      : item.status === "error"
                      ? "border-destructive/30 bg-destructive/5"
                      : ""
                  }
                >
                  <CardContent className="space-y-2 p-4">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          {item.status === "ok" ? (
                            <CheckCircle2 className="h-4 w-4 text-success" />
                          ) : item.status === "error" ? (
                            <XCircle className="h-4 w-4 text-destructive" />
                          ) : null}
                          <span className="truncate font-semibold">
                            {item.supplier}
                          </span>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {item.type_doc}
                          {item.fic_number && ` · ${item.fic_number}`}
                        </div>
                      </div>
                    </div>
                    <div className="text-lg font-semibold tabular-nums">
                      {formatCurrency(item.total_net)}
                    </div>
                    {item.error && (
                      <div className="font-mono text-xs text-destructive">
                        {item.error}
                      </div>
                    )}
                    {item.fic_url && (
                      <Button asChild size="sm" variant="ghost" className="h-7 px-2">
                        <a href={item.fic_url} target="_blank" rel="noreferrer">
                          Apri su FiC <ExternalLink className="h-3 w-3" />
                        </a>
                      </Button>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
