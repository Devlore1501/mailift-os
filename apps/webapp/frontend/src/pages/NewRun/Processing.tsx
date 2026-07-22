import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { Loader2, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  useClassifyStatement,
  useJob,
  useParseStatement,
} from "@/lib/queries";
import type { Transaction } from "@/types/api";
import { ApiError } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

export function Processing() {
  const { statementId } = useParams<{ statementId: string }>();
  const navigate = useNavigate();
  const [jobId, setJobId] = useState<string | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [started, setStarted] = useState(false);

  const parse = useParseStatement();
  const classify = useClassifyStatement();
  const job = useJob(jobId);

  useEffect(() => {
    if (!statementId || started) return;
    setStarted(true);
    (async () => {
      try {
        const parseRes = await parse.mutateAsync(statementId);
        setTransactions(parseRes.transactions);
        const classifyRes = await classify.mutateAsync(statementId);
        setJobId(classifyRes.job_id);
      } catch (err) {
        const msg = err instanceof ApiError ? err.message : String(err);
        setError(msg);
        toast.error("Elaborazione fallita", { description: msg });
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statementId, started]);

  useEffect(() => {
    if (!job.data) return;
    if (job.data.status === "done") {
      const t = setTimeout(
        () => navigate(`/new/verify/${statementId}`),
        500
      );
      return () => clearTimeout(t);
    }
    if (job.data.status === "error") {
      setError(job.data.error || "Errore sconosciuto");
    }
  }, [job.data, navigate, statementId]);

  const progress = job.data?.progress ?? (parse.isPending ? 15 : 5);
  const stepName =
    error
      ? "Errore"
      : job.data?.step_name ||
        (parse.isPending
          ? "Parsing estratto conto..."
          : classify.isPending
          ? "Avvio classificazione..."
          : jobId
          ? "In attesa..."
          : "Preparazione...");

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Elaborazione fallita</AlertTitle>
        <AlertDescription className="mt-2 space-y-3">
          <div className="text-xs font-mono">{error}</div>
          <Button asChild size="sm" variant="outline">
            <Link to="/new">Torna indietro</Link>
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
            Elaborazione in corso
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Progress value={progress} />
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">{stepName}</span>
            <span className="text-muted-foreground">{progress}%</span>
          </div>
        </CardContent>
      </Card>

      {transactions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Transazioni estratte ({transactions.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="max-h-[360px] overflow-y-auto rounded-md border border-border/60">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-muted/60 text-left">
                  <tr>
                    <th className="px-3 py-2 font-medium">Data</th>
                    <th className="px-3 py-2 font-medium">Descrizione</th>
                    <th className="px-3 py-2 text-right font-medium">Importo</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.slice(0, 100).map((t, i) => (
                    <tr key={i} className="border-t border-border/40">
                      <td className="px-3 py-1.5 tabular-nums">{t.date}</td>
                      <td className="max-w-[420px] truncate px-3 py-1.5">
                        {t.description}
                      </td>
                      <td className="px-3 py-1.5 text-right tabular-nums">
                        {formatCurrency(t.amount, t.currency)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
