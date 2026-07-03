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
import { formatDate, nextMonday } from "@/lib/utils";

export function Plans() {
  const { brandId: brandIdParam } = useParams();
  const brandId = Number(brandIdParam);
  const navigate = useNavigate();

  const { data: brand } = useBrand(brandId);
  const { data: plans, isLoading } = usePlans(brandId);
  const generatePlan = useGeneratePlan(brandId);
  const deletePlan = useDeletePlan(brandId);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [weekStart, setWeekStart] = useState(nextMonday());
  const [numEmails, setNumEmails] = useState<number | "">("");
  const [notes, setNotes] = useState("");

  const effectiveNumEmails =
    numEmails === "" ? (brand?.emails_per_week ?? 3) : numEmails;

  function openDialog() {
    setWeekStart(nextMonday());
    setNumEmails(brand?.emails_per_week ?? 3);
    setNotes("");
    setDialogOpen(true);
  }

  function handleGenerate() {
    if (!weekStart) {
      toast.error("Seleziona la settimana di inizio");
      return;
    }
    generatePlan.mutate(
      {
        week_start: weekStart,
        num_emails: Number(effectiveNumEmails) || 3,
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
            toast.error("Esiste già un piano per quella settimana");
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
            {brand ? `Piani settimanali di ${brand.name}` : "Piani settimanali"}
          </p>
        </div>
        <Button size="lg" onClick={openDialog}>
          <Sparkles className="h-4 w-4" />
          Genera piano settimanale
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
          description="Genera il primo piano editoriale settimanale per questo brand: Claude userà profilo, catalogo e dati Klaviyo."
          action={
            <Button onClick={openDialog}>
              <Sparkles className="h-4 w-4" />
              Genera piano settimanale
            </Button>
          }
        />
      ) : (
        <div className="rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Settimana</TableHead>
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
                      Settimana del {formatDate(plan.week_start)}
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
                            `Eliminare il piano della settimana del ${formatDate(plan.week_start)}?`
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
            <DialogTitle>Genera piano settimanale</DialogTitle>
            <DialogDescription>
              Claude genererà un piano completo usando profilo brand, catalogo,
              offerte e insight Klaviyo.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="week-start">Settimana (lunedì di inizio)</Label>
              <Input
                id="week-start"
                type="date"
                value={weekStart}
                onChange={(e) => setWeekStart(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="num-emails">Numero email</Label>
              <Input
                id="num-emails"
                type="number"
                min={1}
                max={7}
                value={effectiveNumEmails}
                onChange={(e) =>
                  setNumEmails(
                    e.target.value === "" ? "" : Number(e.target.value)
                  )
                }
              />
              <p className="text-xs text-muted-foreground">
                Default: {brand?.emails_per_week ?? 3} email a settimana (dal
                profilo brand).
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
