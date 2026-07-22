import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useJob } from "@/lib/queries";
import type { CreateJobResult, CreatedItem } from "@/types/api";
import { formatCurrency } from "@/lib/utils";

export function Creating() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const job = useJob(jobId);

  useEffect(() => {
    if (job.data?.status === "done") {
      const t = setTimeout(() => navigate(`/new/results/${jobId}`), 500);
      return () => clearTimeout(t);
    }
  }, [job.data?.status, jobId, navigate]);

  const status = job.data?.status;
  const progress = job.data?.progress ?? 0;
  const stepName = job.data?.step_name || "In attesa...";
  const partial =
    (job.data?.result as CreateJobResult | null)?.items ?? [];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {status === "done" ? (
              <CheckCircle2 className="h-4 w-4 text-success" />
            ) : (
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
            )}
            Creazione in corso
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

      {partial.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Autofatture ({partial.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1">
              {partial.map((item: CreatedItem, i) => (
                <li
                  key={i}
                  className="flex items-center justify-between rounded-md border border-border/40 px-3 py-2 text-sm"
                >
                  <div className="flex items-center gap-2">
                    {item.status === "ok" ? (
                      <CheckCircle2 className="h-4 w-4 text-success" />
                    ) : item.status === "error" ? (
                      <XCircle className="h-4 w-4 text-destructive" />
                    ) : (
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                    )}
                    <span className="font-medium">{item.supplier}</span>
                    <span className="text-xs text-muted-foreground">
                      {item.type_doc}
                    </span>
                  </div>
                  <span className="text-xs tabular-nums">
                    {formatCurrency(item.total_net)}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
