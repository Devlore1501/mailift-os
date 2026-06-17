import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Loader2,
  CheckCircle2,
  Minus,
  AlertTriangle,
  FileText,
  ArrowRight,
  SkipForward,
} from "lucide-react";
import { toast } from "sonner";
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
import { Skeleton } from "@/components/ui/skeleton";
import { SupplierBadge } from "@/components/domain/SupplierBadge";
import { PdfPreviewDialog } from "@/components/domain/PdfPreviewDialog";
import {
  useJob,
  useVerifyResults,
  useVerifySuppliers,
} from "@/lib/queries";
import { ApiError } from "@/lib/api";
import type { VerifyStatus } from "@/types/api";

function StatusCell({ status }: { status: VerifyStatus }) {
  if (status === "pending") {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
        <Loader2 className="h-3.5 w-3.5 animate-spin" /> in corso
      </span>
    );
  }
  if (status === "verified") {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-success">
        <CheckCircle2 className="h-3.5 w-3.5" /> verificato
      </span>
    );
  }
  if (status === "pdf_only") {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-amber-600 dark:text-amber-400">
        <CheckCircle2 className="h-3.5 w-3.5" /> PDF scaricato
      </span>
    );
  }
  if (status === "bill_to_mismatch") {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-warning">
        <AlertTriangle className="h-3.5 w-3.5" /> bill-to mismatch
      </span>
    );
  }
  if (status === "not_found") {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
        <Minus className="h-3.5 w-3.5" /> non trovato
      </span>
    );
  }
  return <span className="text-xs text-muted-foreground">{status}</span>;
}

export function VerifySuppliers() {
  const { statementId } = useParams<{ statementId: string }>();
  const navigate = useNavigate();
  const verify = useVerifySuppliers();
  const [jobId, setJobId] = useState<string | null>(null);
  const [started, setStarted] = useState(false);
  const [pdfOpen, setPdfOpen] = useState<string | null>(null); // supplier_key
  const [pdfSupplier, setPdfSupplier] = useState<string>("");

  const job = useJob(jobId);
  const jobDone = job.data?.status === "done";
  const jobError = job.data?.status === "error";

  const results = useVerifyResults(statementId, {
    refetchInterval: jobDone || jobError ? false : 2000,
  });

  useEffect(() => {
    if (!statementId || started) return;
    setStarted(true);
    (async () => {
      try {
        const res = await verify.mutateAsync(statementId);
        setJobId(res.job_id);
      } catch (err) {
        const msg = err instanceof ApiError ? err.message : String(err);
        toast.error("Verifica fallita", { description: msg });
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statementId, started]);

  const items = results.data?.results ?? [];
  const stats = useMemo(() => {
    const verified = items.filter(
      (i) => i.status === "verified" || i.status === "pdf_only"
    ).length;
    const warnings = items.filter(
      (i) => i.status === "bill_to_mismatch"
    ).length;
    return { verified, warnings, total: items.length };
  }, [items]);

  const goNext = () => navigate(`/new/review/${statementId}`);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {jobDone ? (
              <CheckCircle2 className="h-4 w-4 text-success" />
            ) : (
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
            )}
            Verifica fornitori
          </CardTitle>
          <CardDescription>
            Sto cercando le fatture originali nei tuoi account Gmail per
            verificare i dati fiscali dei fornitori...
            {job.data?.step_name && (
              <span className="ml-2 font-mono text-xs">
                {job.data.step_name}
              </span>
            )}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {results.isLoading && items.length === 0 ? (
            <div className="space-y-2">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          ) : items.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              Nessun fornitore trovato.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Fornitore</TableHead>
                    <TableHead>Paese</TableHead>
                    <TableHead>P.IVA</TableHead>
                    <TableHead>Stato</TableHead>
                    <TableHead>PDF</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((r) => {
                    const country =
                      (r.extracted?.supplier_country as string | undefined) ||
                      "";
                    const vat =
                      (r.extracted?.supplier_vat_number as string | undefined) ||
                      "";
                    return (
                      <TableRow key={r.supplier_key}>
                        <TableCell className="font-medium">
                          {r.supplier_name}
                        </TableCell>
                        <TableCell>
                          <SupplierBadge countryIso={country} />
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {vat || "—"}
                        </TableCell>
                        <TableCell>
                          <StatusCell status={r.status} />
                        </TableCell>
                        <TableCell>
                          {r.pdf_count > 0 ? (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                setPdfSupplier(r.supplier_name);
                                setPdfOpen(r.supplier_key);
                              }}
                            >
                              <FileText className="h-3.5 w-3.5" />
                              {r.pdf_count}
                            </Button>
                          ) : (
                            <span className="text-xs text-muted-foreground">
                              —
                            </span>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex items-center justify-between rounded-md border border-border/60 bg-muted/20 px-4 py-3">
        <div className="text-xs text-muted-foreground">
          <span className="font-medium text-foreground">{stats.verified}</span>{" "}
          verificati ·{" "}
          <span className="font-medium text-foreground">{stats.total}</span>{" "}
          totali
          {stats.warnings > 0 && (
            <>
              {" "}
              ·{" "}
              <span className="font-medium text-warning">
                {stats.warnings} warning
              </span>
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" onClick={goNext}>
            <SkipForward className="h-4 w-4" />
            Salta verifica
          </Button>
          <Button disabled={!jobDone && !jobError} onClick={goNext}>
            Avanti
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <PdfPreviewDialog
        supplierKey={pdfOpen ?? ""}
        supplierName={pdfSupplier}
        open={!!pdfOpen}
        onOpenChange={(o) => {
          if (!o) setPdfOpen(null);
        }}
      />
    </div>
  );
}
