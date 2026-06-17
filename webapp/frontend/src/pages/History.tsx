import { useState } from "react";
import { Link } from "react-router-dom";
import { FileText, FlaskConical } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/domain/EmptyState";
import { useHistory } from "@/lib/queries";
import { formatDate } from "@/lib/utils";

type Filter = "all" | "ok" | "errors" | "dry" | "live";

export function History() {
  const { data, isLoading } = useHistory();
  const [filter, setFilter] = useState<Filter>("all");

  const runs = (data ?? []).filter((r) => {
    if (filter === "ok") return r.error_count === 0 && r.created_count > 0;
    if (filter === "errors") return r.error_count > 0;
    if (filter === "dry") return r.dry_run;
    if (filter === "live") return !r.dry_run;
    return true;
  });

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Storico</h1>
        <p className="text-sm text-muted-foreground">
          Tutti i run passati
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {(
          [
            ["all", "Tutti"],
            ["ok", "Solo OK"],
            ["errors", "Con errori"],
            ["dry", "Dry-run"],
            ["live", "Live"],
          ] as [Filter, string][]
        ).map(([key, label]) => (
          <Button
            key={key}
            size="sm"
            variant={filter === key ? "default" : "outline"}
            onClick={() => setFilter(key)}
          >
            {label}
          </Button>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Run ({runs.length})</CardTitle>
          <CardDescription>Click su una riga per i dettagli</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-9 w-full" />
            </div>
          ) : runs.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="Nessun run"
              description="Nessun run passato corrispondente al filtro."
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Data</TableHead>
                    <TableHead>Statement</TableHead>
                    <TableHead className="text-right">Totale</TableHead>
                    <TableHead className="text-right">Ok</TableHead>
                    <TableHead className="text-right">Errori</TableHead>
                    <TableHead>Tipo</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runs.map((r) => (
                    <TableRow
                      key={r.id}
                      className="cursor-pointer"
                      onClick={() => {
                        window.location.href = `/history/${r.id}`;
                      }}
                    >
                      <TableCell className="text-xs">
                        <Link to={`/history/${r.id}`}>
                          {formatDate(r.started_at, "short")}
                        </Link>
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate font-mono text-xs">
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
