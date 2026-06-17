import { Link, useParams } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  Home,
  Plus,
  XCircle,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { useJob } from "@/lib/queries";
import { formatCurrency } from "@/lib/utils";
import type { CreateJobResult, CreatedItem } from "@/types/api";

export function Results() {
  const { jobId } = useParams<{ jobId: string }>();
  const job = useJob(jobId, { interval: 2000 });

  if (job.isLoading || !job.data) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  const result = job.data.result as CreateJobResult | null;
  const items: CreatedItem[] = result?.items ?? [];
  const dryRun = result?.dry_run ?? false;
  const created = items.filter((i) => i.status === "ok");
  const errors = items.filter((i) => i.status === "error");
  const skipped = items.filter((i) => i.status === "skipped");

  return (
    <div className="space-y-6">
      {!dryRun && created.length > 0 && (
        <Alert variant="warning">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Le autofatture sono state create come BOZZA</AlertTitle>
          <AlertDescription>
            Vai su Fatture in Cloud → Autofatture, verifica ognuna e clicca
            <strong> Firma e invia</strong> per completare l&apos;invio al SDI.
          </AlertDescription>
        </Alert>
      )}

      {dryRun && (
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Simulazione (dry-run)</AlertTitle>
          <AlertDescription>
            Nessuna autofattura e&apos; stata effettivamente creata su Fatture
            in Cloud. Per creare davvero, passa a modalita&apos; Live.
          </AlertDescription>
        </Alert>
      )}

      {/* Created */}
      {(created.length > 0 || skipped.length > 0) && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-success" />
              {dryRun
                ? `${skipped.length} simulate`
                : `${created.length} create`}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {(dryRun ? skipped : created).map((item, i) => (
                <Card
                  key={i}
                  className="border-success/30 bg-success/5"
                >
                  <CardContent className="space-y-2 p-4">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate font-semibold">
                          {item.supplier}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {item.type_doc}
                          {item.fic_number &&
                            ` · ${item.fic_number}${
                              item.fic_numeration
                                ? `/${item.fic_numeration}`
                                : ""
                            }`}
                        </div>
                      </div>
                    </div>
                    <div className="text-lg font-semibold tabular-nums">
                      {formatCurrency(item.total_net)}
                    </div>
                    {item.fic_url && (
                      <Button
                        asChild
                        size="sm"
                        variant="ghost"
                        className="h-7 px-2"
                      >
                        <a
                          href={item.fic_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Apri su FiC
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      </Button>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Errors */}
      {errors.length > 0 && (
        <Card className="border-destructive/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <XCircle className="h-4 w-4" />
              {errors.length} errori
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {errors.map((e, i) => (
                <li
                  key={i}
                  className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm"
                >
                  <div className="font-medium">{e.supplier}</div>
                  {e.error && (
                    <div className="mt-1 font-mono text-xs text-muted-foreground">
                      {e.error}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-wrap gap-2">
        <Button asChild>
          <Link to="/">
            <Home className="h-4 w-4" /> Torna alla dashboard
          </Link>
        </Button>
        <Button asChild variant="outline">
          <Link to="/new">
            <Plus className="h-4 w-4" /> Nuovo run
          </Link>
        </Button>
      </div>
    </div>
  );
}
