import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { CalendarDays, Mail, Sparkles, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/domain/EmptyState";
import { PlanStatusBadge } from "@/components/domain/PlanStatusBadge";
import {
  useBrand,
  useDeletePlan,
  useGeneratePlan,
  usePlans,
} from "@/lib/queries";
import { formatMonth, nextMonthStart } from "@/lib/utils";

export function Plans() {
  const { brandId: brandIdParam } = useParams();
  const brandId = Number(brandIdParam);
  const navigate = useNavigate();

  const { data: brand } = useBrand(brandId);
  const { data: plans, isLoading } = usePlans(brandId);
  const generatePlan = useGeneratePlan(brandId);
  const deletePlan = useDeletePlan(brandId);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [monthStart, setMonthStart] = useState(nextMonthStart());
  const [numEmails, setNumEmails] = useState<number | "">("");
  const [notes, setNotes] = useState("");

  const defaultMonthly = (brand?.emails_per_week ?? 3) * 4;
  const effectiveNumEmails = numEmails === "" ? defaultMonthly : numEmails;

  function openDialog() {
    setMonthStart(nextMonthStart());
    setNumEmails(defaultMonthly);
    setNotes("");
    setDialogOpen(true);
  }

  function handleGenerate() {
    if (!monthStart) {
      toast.error("Seleziona il mese");
      return;
    }
    generatePlan.mutate(
      {
        month_start: monthStart,
        num_emails: Number(effectiveNumEmails) || defaultMonthly,
        notes: notes.trim() || undefined,
      },
      {
        onSuccess: (plan) => {
          setDialogOpen(false);
          toast.success("Generazione avviata");
          navigate(`/brands/${brandId}/plans/${plan.id}`);
        },
        onError: (err) => {
          if (err.status === 409) {
            toast.error("Esiste già un piano per quel mese");
          } else {
            toast.error(`Errore: ${err.message}`);
          }
        },
      }
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight">
            Piani editoriali
          </h1>
          <p className="text-sm text-muted-foreground">
            {brand ? `Calendari mensili di ${brand.name}` : "Calendari mensili"}
          </p>
        </div>
        <Button size="lg" onClick={openDialog}>
          <Sparkles className="h-4 w-4" />
          Genera piano mensile
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : (plans ?? []).length === 0 ? (
        <EmptyState
          icon={CalendarDays}
          title="Nessun piano"
          description="Genera il primo calendario editoriale mensile per questo brand: Claude userà profilo, catalogo, dati Klaviyo e le festività del paese."
          action={
            <Button onClick={openDialog}>
              <Sparkles className="h-4 w-4" />
              Genera piano mensile
            </Button>
          }
        />
      ) : (
        <div className="rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Mese</TableHead>
                <TableHead>Stato</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Note</TableHead>
                <TableHead className="w-[60px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(plans ?? []).map((plan) => (
                <TableRow
                  key={plan.id}
                  className="cursor-pointer"
                  onClick={() =>
                    navigate(`/brands/${brandId}/plans/${plan.id}`)
                  }
                >
                  <TableCell>
                    <Link
                      to={`/brands/${brandId}/plans/${plan.id}`}
                      className="font-medium hover:underline"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <span className="capitalize">{formatMonth(plan.month_start)}</span>
                    </Link>
                  </TableCell>
                  <TableCell>
                    <PlanStatusBadge status={plan.status} />
                  </TableCell>
                  <TableCell>
                    <span className="inline-flex items-center gap-1 text-sm text-muted-foreground">
                      <Mail className="h-3.5 w-3.5" />
                      {plan.num_emails}
                    </span>
                  </TableCell>
                  <TableCell className="max-w-[240px] truncate text-sm text-muted-foreground">
                    {plan.notes || "—"}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Elimina piano"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (
                          window.confirm(
                            `Eliminare il piano di ${formatMonth(plan.month_start)}?`
                          )
                        ) {
                          deletePlan.mutate(plan.id, {
                            onSuccess: () => toast.success("Piano eliminato"),
                            onError: (err) =>
                              toast.error(`Errore: ${err.message}`),
                          });
                        }
                      }}
                    >
                      <Trash2 className="h-4 w-4 text-muted-foreground" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Genera piano mensile</DialogTitle>
            <DialogDescription>
              Claude genererà il calendario del mese (regola 70% educativo /
              20% prodotto / 10% promo) usando profilo brand, catalogo, offerte,
              insight Klaviyo e le festività del paese.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="month-start">Mese</Label>
              <Input
                id="month-start"
                type="month"
                value={monthStart.slice(0, 7)}
                onChange={(e) =>
                  setMonthStart(e.target.value ? `${e.target.value}-01` : "")
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="num-emails">Numero email nel mese</Label>
              <Input
                id="num-emails"
                type="number"
                min={2}
                max={31}
                value={effectiveNumEmails}
                onChange={(e) =>
                  setNumEmails(
                    e.target.value === "" ? "" : Number(e.target.value)
                  )
                }
              />
              <p className="text-xs text-muted-foreground">
                Default: {defaultMonthly} email al mese ({brand?.emails_per_week ?? 3}
                /settimana × 4, dal profilo brand).
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="plan-notes">Note per la generazione</Label>
              <Textarea
                id="plan-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="es. focus sulla flash sale di fine mese, tono estivo…"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Annulla
            </Button>
            <Button onClick={handleGenerate} disabled={generatePlan.isPending}>
              <Sparkles className="h-4 w-4" />
              {generatePlan.isPending ? "Avvio…" : "Genera piano"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
