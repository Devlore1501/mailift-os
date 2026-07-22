import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { FileText, AlertCircle, ChevronDown } from "lucide-react";
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
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { SupplierBadge } from "@/components/domain/SupplierBadge";
import { VatBadge } from "@/components/domain/VatBadge";
import { BillToWarning } from "@/components/domain/BillToWarning";
import { PdfPreviewDialog } from "@/components/domain/PdfPreviewDialog";
import {
  useCreateAutofatture,
  usePreview,
} from "@/lib/queries";
import { ApiError } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
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

  const handleCreate = async () => {
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

  return (
    <div className="space-y-6">
      {preview.skipped_italian.length > 0 && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>
            {preview.skipped_italian.length} transazioni escluse
          </AlertTitle>
          <AlertDescription>
            <div className="mt-1 text-xs text-muted-foreground">
              Fornitori italiani con IVA 22% diretta — non richiedono
              autofattura.
            </div>
            <Accordion type="single" collapsible className="mt-2">
              <AccordionItem value="skipped" className="border-0">
                <AccordionTrigger className="py-2 text-xs">
                  Mostra dettagli
                </AccordionTrigger>
                <AccordionContent>
                  <ul className="space-y-1 text-xs">
                    {preview.skipped_italian.map((s, i) => (
                      <li
                        key={i}
                        className="flex items-center justify-between border-b border-border/40 py-1"
                      >
                        <span className="font-medium">{s.supplier_name}</span>
                        <span className="text-muted-foreground">{s.reason}</span>
                        <span className="tabular-nums">
                          {formatCurrency(Math.abs(s.amount))}
                        </span>
                      </li>
                    ))}
                  </ul>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </AlertDescription>
        </Alert>
      )}

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
                        {a.supplier_vat_number && (
                          <div className="text-[10px] font-mono text-muted-foreground">
                            {a.supplier_vat_number}
                          </div>
                        )}
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
            onClick={handleCreate}
            disabled={createMut.isPending || nonExcludedCount === 0}
          >
            {dryRun
              ? `Simula creazione (${nonExcludedCount})`
              : `Crea e salva su FiC (${nonExcludedCount})`}
          </Button>
        </CardContent>
      </Card>

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
