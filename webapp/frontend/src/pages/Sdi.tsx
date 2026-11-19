import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router";
import { useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Loader2, RefreshCw, Send, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ApiError } from "@/lib/api";
import { useJob, useSdiDocuments, useSdiSend, useSdiVerify } from "@/lib/queries";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { SdiDocument, SdiJobItem, SdiJobResult } from "@/types/api";

const CONFIRM_WORD = "INVIA";
const SENT_STATES = new Set(["pending", "processing", "sent", "delivered", "not_delivered", "rejected"]);

const STATUS_LABEL: Record<string, { label: string; variant: "zinc" | "blue" | "amber" | "red" | "success" }> = {
  sent: { label: "Inviata", variant: "blue" },
  delivered: { label: "Consegnata", variant: "success" },
  not_delivered: { label: "Non consegnata", variant: "amber" },
  rejected: { label: "Scartata", variant: "red" },
  pending: { label: "In invio", variant: "blue" },
  processing: { label: "In invio", variant: "blue" },
};

function StatusBadge({ doc, check }: { doc: SdiDocument; check?: SdiJobItem }) {
  const s = doc.ei_status ? STATUS_LABEL[doc.ei_status] : undefined;
  if (s) return <Badge variant={s.variant}>{s.label}</Badge>;
  if (check?.status === "ok") return <Badge variant="success">Verifica OK</Badge>;
  if (check?.status === "invalid") return <Badge variant="red" title={check.detail}>Da correggere</Badge>;
  return <Badge variant="zinc">Da inviare</Badge>;
}

export function Sdi() {
  const [params] = useSearchParams();
  const ids = useMemo(
    () => params.get("ids")?.split(",").map(Number).filter(Boolean),
    [params]
  );
  const [date, setDate] = useState<string | undefined>(params.get("date") ?? undefined);
  const qc = useQueryClient();
  const docsQ = useSdiDocuments({ date: ids ? undefined : date, ids });
  const docs = docsQ.data?.documents ?? [];

  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [checks, setChecks] = useState<Record<number, SdiJobItem>>({});
  const [jobId, setJobId] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const verify = useSdiVerify();
  const send = useSdiSend();
  const job = useJob(jobId);

  const sendable = docs.filter((d) => !SENT_STATES.has(d.ei_status ?? ""));
  useEffect(() => {
    setSelected(new Set(sendable.map((d) => d.id)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docsQ.data]);

  useEffect(() => {
    if (job.data?.status === "done") {
      const res = job.data.result as SdiJobResult;
      setChecks((prev) => ({ ...prev, ...Object.fromEntries(res.items.map((i) => [i.id, i])) }));
      if (job.data.kind === "sdi_send") {
        toast.success(`${res.sent ?? 0} inviate al SDI`, {
          description: res.errors ? `${res.errors} non inviate: vedi la tabella` : undefined,
        });
        qc.invalidateQueries({ queryKey: ["sdi-documents"] });
      }
      setJobId(null);
    } else if (job.data?.status === "error") {
      toast.error("Operazione fallita", { description: job.data.error ?? undefined });
      setJobId(null);
    }
  }, [job.data, qc]);

  const busy = !!jobId || verify.isPending || send.isPending;
  const chosen = sendable.filter((d) => selected.has(d.id));
  const chosenGross = chosen.reduce((sum, d) => sum + d.amount_gross, 0);

  async function run(kind: "verify" | "send") {
    try {
      const doc_ids = chosen.map((d) => d.id);
      const res =
        kind === "verify"
          ? await verify.mutateAsync(doc_ids)
          : await send.mutateAsync({ doc_ids, confirm: confirmText });
      setJobId(res.job_id);
      setConfirmOpen(false);
      setConfirmText("");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : String(err));
    }
  }

  const toggle = (id: number, on: boolean) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (on) next.add(id);
      else next.delete(id);
      return next;
    });

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-1.5">
            <CardTitle>Invio al SDI</CardTitle>
            <CardDescription>
              {ids
                ? `${docs.length} autofatture dell'ultimo run`
                : `Autofatture con data ${docsQ.data?.date ? formatDate(docsQ.data.date) : "…"}`}
            </CardDescription>
          </div>
          {!ids && (
            <div className="flex items-end gap-2">
              <div className="space-y-1">
                <Label htmlFor="sdi-date" className="text-xs">Data documento</Label>
                <Input
                  id="sdi-date"
                  type="date"
                  className="h-9 w-40"
                  value={date ?? docsQ.data?.date ?? ""}
                  onChange={(e) => setDate(e.target.value || undefined)}
                />
              </div>
              <Button variant="outline" size="icon" aria-label="Aggiorna stati" onClick={() => docsQ.refetch()}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          )}
        </CardHeader>
        <CardContent>
          {docsQ.isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          ) : docsQ.isError ? (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Fatture in Cloud non raggiungibile</AlertTitle>
              <AlertDescription>{(docsQ.error as Error).message}</AlertDescription>
            </Alert>
          ) : docs.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nessuna autofattura per questa data.</p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-10" />
                    <TableHead>Numero</TableHead>
                    <TableHead>Fornitore</TableHead>
                    <TableHead className="text-right">Lordo</TableHead>
                    <TableHead>Stato</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {docs.map((d) => {
                    const canSend = !SENT_STATES.has(d.ei_status ?? "");
                    const check = checks[d.id];
                    return (
                      <TableRow key={d.id}>
                        <TableCell>
                          <Checkbox
                            checked={canSend && selected.has(d.id)}
                            disabled={!canSend || busy}
                            onCheckedChange={(v) => toggle(d.id, !!v)}
                            aria-label={`Seleziona ${d.number}`}
                          />
                        </TableCell>
                        <TableCell className="font-mono text-xs">{d.number}</TableCell>
                        <TableCell className="max-w-[260px]">
                          <div className="truncate font-medium">{d.supplier}</div>
                          {(d.rejection_reason || (check && check.status !== "ok" && check.detail)) && (
                            <div className="mt-0.5 text-xs text-destructive">
                              {d.rejection_reason ?? check?.detail}
                            </div>
                          )}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">{formatCurrency(d.amount_gross)}</TableCell>
                        <TableCell>
                          <StatusBadge doc={d} check={check} />
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

      {sendable.length > 0 && (
        <Card>
          <CardContent className="flex flex-wrap items-center justify-between gap-4 p-4">
            <div className="text-sm">
              <span className="text-muted-foreground">Selezionate:</span>{" "}
              <span className="font-semibold tabular-nums">{chosen.length}</span>
              <span className="mx-2 text-muted-foreground">·</span>
              <span className="font-semibold tabular-nums">{formatCurrency(chosenGross)}</span>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" disabled={busy || chosen.length === 0} onClick={() => run("verify")}>
                {busy && job.data?.kind === "sdi_verify" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <ShieldCheck className="h-4 w-4" />
                )}
                Verifica formale
              </Button>
              <Button disabled={busy || chosen.length === 0} onClick={() => setConfirmOpen(true)}>
                {busy && job.data?.kind === "sdi_send" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
                Invia al SDI
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {busy && job.data && (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> {job.data.step_name}
        </p>
      )}
      {docs.length > 0 && sendable.length === 0 && (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <CheckCircle2 className="h-4 w-4 text-success" /> Tutte gia' inviate al SDI.
        </p>
      )}

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Inviare {chosen.length} autofatture al SDI?</DialogTitle>
            <DialogDescription>
              L&apos;invio non si puo&apos; annullare: per correggere un documento
              consegnato serve una nota di variazione. Prima di ogni invio viene
              rifatta la verifica formale; chi non la supera non parte.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <p className="text-sm">
              Totale lordo <span className="font-semibold tabular-nums">{formatCurrency(chosenGross)}</span>
            </p>
            <Label htmlFor="sdi-confirm" className="text-xs">
              Scrivi {CONFIRM_WORD} per confermare
            </Label>
            <Input
              id="sdi-confirm"
              autoComplete="off"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>
              Annulla
            </Button>
            <Button
              variant="destructive"
              disabled={confirmText.trim() !== CONFIRM_WORD || busy}
              onClick={() => run("send")}
            >
              Invia al SDI
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
