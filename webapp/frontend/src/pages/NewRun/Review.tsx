import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { FileText, ShieldAlert, Copy } from "lucide-react";
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
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { DuplicateBadge } from "@/components/domain/DuplicateBadge";
import { ExcludedList } from "@/components/domain/ExcludedList";
import { SupplierBadge } from "@/components/domain/SupplierBadge";
import { VatBadge } from "@/components/domain/VatBadge";
import { BillToWarning } from "@/components/domain/BillToWarning";
import { PdfPreviewDialog } from "@/components/domain/PdfPreviewDialog";
import {
  useCreateAutofatture,
  usePreview,
} from "@/lib/queries";
import { ApiError } from "@/lib/api";
import { formatCurrency, formatMonth } from "@/lib/utils";
import { getStoredEnvironment } from "@/components/domain/EnvironmentSwitch";
import type { AutofatturaPayload, PreviewResponse } from "@/types/api";

type RowState = {
  excluded: boolean;
  description: string;
  amount_net: number;
};

// supplier_key arriva direttamente dal backend (workflow.py normalize_key).
// Fallback euristico solo nel caso in cui il payload non lo contenga (vecchi statement
// creati prima dell'update schema — legacy non-breaking).
function slugifySupplier(a: AutofatturaPayload): string {
  if (a.supplier_key) return a.supplier_key;
  return a.supplier_name
    .toLowerCase()
    .replace(/\b(inc|ltd|llc|s\.?r\.?l\.?|ab|gmbh|srl|bv|oy|labs|tech)\b/g, "")
    .replace(/[^a-z0-9]+/g, "")
    .trim();
}

export function Review() {
  const { statementId } = useParams<{ statementId: string }>();
  const navigate = useNavigate();
  const previewMut = usePreview();
  const createMut = useCreateAutofatture();

  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [rowStates, setRowStates] = useState<Record<string, RowState>>({});
  const [loaded, setLoaded] = useState(false);
  const [pdfOpenKey, setPdfOpenKey] = useState<string | null>(null);
  const [pdfSupplierName, setPdfSupplierName] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);

  useEffect(() => {
    if (!statementId || loaded) return;
    setLoaded(true);
    (async () => {
      try {
        const res = await previewMut.mutateAsync(statementId);
        setPreview(res);
        const states: Record<string, RowState> = {};
        for (const a of res.autofatture) {
          const firstLine = a.lines[0];
          states[a.id] = {
            excluded: a.excluded,
            description: firstLine?.description ?? "",
            amount_net: firstLine?.amount_net ?? 0,
          };
        }
        setRowStates(states);
      } catch (err) {
        const msg = err instanceof ApiError ? err.message : String(err);
        toast.error("Preview fallita", { description: msg });
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statementId, loaded]);

  const updateRow = (id: string, patch: Partial<RowState>) => {
    setRowStates((prev) => ({ ...prev, [id]: { ...prev[id], ...patch } }));
  };

  const totals = useMemo(() => {
    if (!preview) return {} as Record<string, number>;
    const t: Record<string, number> = {};
    for (const a of preview.autofatture) {
      const s = rowStates[a.id];
      if (!s || s.excluded) continue;
      const cur = a.currency || "EUR";
      t[cur] = (t[cur] || 0) + s.amount_net;
    }
    return t;
  }, [preview, rowStates]);

  const selected = useMemo(
    () => (preview?.autofatture ?? []).filter((a) => rowStates[a.id] && !rowStates[a.id].excluded),
    [preview, rowStates]
  );

  const handleCreate = async () => {
    setConfirmOpen(false);
    if (!preview) return;
    const env = getStoredEnvironment();
    const dryRun = env === "dry-run";
    const payload: AutofatturaPayload[] = preview.autofatture
      .filter((a) => {
        const s = rowStates[a.id];
        return s && !s.excluded;
      })
      .map((a) => {
        const s = rowStates[a.id];
        const firstLine = a.lines[0];
        return {
          ...a,
          excluded: false,
          lines: [
            {
              ...firstLine,
              description: s.description,
              amount_net: s.amount_net,
            },
            ...a.lines.slice(1),
          ],
        };
      });
    if (payload.length === 0) {
      toast.error("Nessuna autofattura selezionata");
      return;
    }
    try {
      const res = await createMut.mutateAsync({
        autofatture: payload,
        dry_run: dryRun,
        statement_id: statementId,
      });
      navigate(`/new/creating/${res.job_id}`);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : String(err);
      toast.error("Creazione fallita", { description: msg });
    }
  };

  if (previewMut.isPending && !preview) {
    return (
      <Card>
        <CardContent className="space-y-3 p-6">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!preview) return null;

  const nonExcludedCount = preview.autofatture.filter(
    (a) => !rowStates[a.id]?.excluded
  ).length;

  const env = getStoredEnvironment();
  const dryRun = env === "dry-run";
  const dupCertain = preview.autofatture.filter((a) => a.duplicate?.level === "duplicate").length;
  const dupPossible = preview.autofatture.filter((a) => a.duplicate?.level === "possible").length;
  const selectedPossibleDup = selected.filter((a) => a.duplicate).length;

  return (
    <div className="space-y-6">
      {!preview.duplicate_check_ok && (
        <Alert variant="destructive">
          <ShieldAlert className="h-4 w-4" />
          <AlertTitle>Controllo duplicati non eseguito</AlertTitle>
          <AlertDescription className="text-xs">
            Fatture in Cloud non ha risposto, quindi non so se queste
            autofatture esistono gia'. Ricarica la pagina prima di crearle.
          </AlertDescription>
        </Alert>
      )}
      {dupCertain + dupPossible > 0 && (
        <Alert variant="warning">
          <Copy className="h-4 w-4" />
          <AlertTitle>
            {dupCertain > 0 && `${dupCertain} gia' emesse (escluse)`}
            {dupCertain > 0 && dupPossible > 0 && " · "}
            {dupPossible > 0 && `${dupPossible} possibili duplicati`}
          </AlertTitle>
          <AlertDescription className="text-xs text-muted-foreground">
            Su FiC esiste gia' un'autofattura stesso fornitore e stesso importo.
            Gli abbonamenti a prezzo fisso si ripetono ogni mese: controlla la
            data dell'autofattura esistente prima di includerli.
          </AlertDescription>
        </Alert>
      )}

      <ExcludedList
        excluded={preview.excluded}
        skippedItalian={preview.skipped_italian}
        orphanRefunds={preview.orphan_refunds}
      />

      <Card>
        <CardHeader>
          <CardTitle>Revisione autofatture</CardTitle>
          <CardDescription>
            Verifica i dati prima di creare le autofatture su Fatture in Cloud
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10"></TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Fornitore</TableHead>
                  <TableHead>Mese</TableHead>
                  <TableHead>Paese</TableHead>
                  <TableHead>IVA</TableHead>
                  <TableHead>Descrizione</TableHead>
                  <TableHead className="text-right">Imponibile</TableHead>
                  <TableHead>Val.</TableHead>
                  <TableHead>PDF</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {preview.autofatture.map((a) => {
                  const s = rowStates[a.id];
                  if (!s) return null;
                  const firstLine = a.lines[0];
                  const verified = a.verify_status === "verified";
                  return (
                    <TableRow
                      key={a.id}
                      className={s.excluded ? "opacity-50" : ""}
                    >
                      <TableCell>
                        <Checkbox
                          checked={!s.excluded}
                          onCheckedChange={(v) =>
                            updateRow(a.id, { excluded: !v })
                          }
                        />
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{a.type_doc}</Badge>
                      </TableCell>
                      <TableCell className="max-w-[200px]">
                        <div className="flex items-center gap-2">
                          <span className="truncate font-medium">
                            {a.supplier_name}
                          </span>
                          {a.billing_data_warning && (
                            <BillToWarning supplier={a.supplier_name} />
                          )}
                        </div>
                        <DuplicateBadge dup={a.duplicate} />
                        {a.supplier_vat_number && (
                          <div className="text-[10px] font-mono text-muted-foreground">
                            {a.supplier_vat_number}
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-xs capitalize">
                        {formatMonth(a.ref_invoice_date)}
                      </TableCell>
                      <TableCell>
                        <SupplierBadge countryIso={a.supplier_country_iso} />
                      </TableCell>
                      <TableCell>
                        <VatBadge
                          vatId={firstLine?.vat_id ?? 0}
                          vatRatePercent={firstLine?.vat_rate_percent}
                        />
                      </TableCell>
                      <TableCell className="min-w-[200px]">
                        <Input
                          value={s.description}
                          onChange={(e) =>
                            updateRow(a.id, { description: e.target.value })
                          }
                          className="h-8"
                        />
                      </TableCell>
                      <TableCell className="w-32 text-right">
                        <Input
                          type="number"
                          step="0.01"
                          value={s.amount_net}
                          onChange={(e) =>
                            updateRow(a.id, {
                              amount_net: parseFloat(e.target.value) || 0,
                            })
                          }
                          className="h-8 text-right tabular-nums"
                        />
                      </TableCell>
                      <TableCell className="text-xs">{a.currency}</TableCell>
                      <TableCell>
                        {verified ? (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => {
                              setPdfSupplierName(a.supplier_name);
                              setPdfOpenKey(slugifySupplier(a));
                            }}
                          >
                            <FileText className="h-3.5 w-3.5" />
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
        </CardContent>
      </Card>

      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-4 p-4">
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Selezionate:</span>{" "}
              <span className="font-semibold tabular-nums">
                {nonExcludedCount}
              </span>
            </div>
            {Object.entries(totals).map(([cur, amount]) => (
              <div key={cur}>
                <span className="text-muted-foreground">Totale {cur}:</span>{" "}
                <span className="font-semibold tabular-nums">
                  {formatCurrency(amount, cur)}
                </span>
              </div>
            ))}
          </div>
          <Button
            size="lg"
            onClick={() => (dryRun ? handleCreate() : setConfirmOpen(true))}
            disabled={createMut.isPending || nonExcludedCount === 0}
          >
            {dryRun
              ? `Simula creazione (${nonExcludedCount})`
              : `Crea e salva su FiC (${nonExcludedCount})`}
          </Button>
        </CardContent>
      </Card>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Creare {nonExcludedCount} autofatture su FiC?</DialogTitle>
            <DialogDescription>
              Vengono salvate su Fatture in Cloud ma non inviate al SDI: l'invio
              e' un passaggio separato.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-1 text-sm">
            {Object.entries(totals).map(([cur, amount]) => (
              <div key={cur} className="flex justify-between">
                <span className="text-muted-foreground">Imponibile {cur}</span>
                <span className="font-semibold tabular-nums">{formatCurrency(amount, cur)}</span>
              </div>
            ))}
            {selectedPossibleDup > 0 && (
              <p className="pt-2 text-warning">
                {selectedPossibleDup} selezionate risultano possibili duplicati.
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>
              Annulla
            </Button>
            <Button onClick={handleCreate} disabled={createMut.isPending}>
              Crea su FiC
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <PdfPreviewDialog
        supplierKey={pdfOpenKey ?? ""}
        supplierName={pdfSupplierName}
        open={!!pdfOpenKey}
        onOpenChange={(o) => {
          if (!o) setPdfOpenKey(null);
        }}
      />
    </div>
  );
}
