import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { CheckCircle2, Package, Plus, Store, Tag, XCircle } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
import { EmptyState } from "@/components/domain/EmptyState";
import { PlanStatusBadge } from "@/components/domain/PlanStatusBadge";
import { useBrands, useCreateBrand } from "@/lib/queries";
import { setLastBrandId } from "@/lib/brand";
import { formatDate } from "@/lib/utils";
import type { BrandSummary } from "@/types/api";

function BrandCard({ brand }: { brand: BrandSummary }) {
  const navigate = useNavigate();

  return (
    <Card
      role="button"
      tabIndex={0}
      className="cursor-pointer transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      onClick={() => {
        setLastBrandId(brand.id);
        navigate(`/brands/${brand.id}/plans`);
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          setLastBrandId(brand.id);
          navigate(`/brands/${brand.id}/plans`);
        }
      }}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base">{brand.name}</CardTitle>
          {brand.klaviyo_configured ? (
            <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
              <CheckCircle2 className="h-3 w-3" />
              Klaviyo
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full border border-border bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
              <XCircle className="h-3 w-3" />
              Klaviyo
            </span>
          )}
        </div>
        <p className="line-clamp-2 min-h-[2rem] text-xs text-muted-foreground">
          {brand.positioning || "Nessun positioning definito"}
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <Package className="h-3.5 w-3.5" />
            {brand.num_products} prodotti
          </span>
          <span className="inline-flex items-center gap-1">
            <Tag className="h-3.5 w-3.5" />
            {brand.num_active_offers} offerte attive
          </span>
        </div>
        <div className="flex items-center justify-between border-t border-border/60 pt-3">
          <span className="text-xs text-muted-foreground">
            Ultimo piano
            {brand.last_plan_week_start
              ? ` · ${formatDate(brand.last_plan_week_start)}`
              : ""}
          </span>
          <PlanStatusBadge status={brand.last_plan_status} />
        </div>
      </CardContent>
    </Card>
  );
}

export function Dashboard() {
  const { data: brands, isLoading } = useBrands();
  const createBrand = useCreateBrand();
  const navigate = useNavigate();
  const location = useLocation();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [name, setName] = useState("");
  const [positioning, setPositioning] = useState("");

  // Il BrandSwitcher può chiedere di aprire il dialog via location state.
  useEffect(() => {
    if ((location.state as { openNewBrand?: boolean } | null)?.openNewBrand) {
      setDialogOpen(true);
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [location.state, location.pathname, navigate]);

  function handleCreate() {
    const trimmed = name.trim();
    if (!trimmed) {
      toast.error("Il nome del brand è obbligatorio");
      return;
    }
    createBrand.mutate(
      { name: trimmed, positioning: positioning.trim() || undefined },
      {
        onSuccess: (brand) => {
          toast.success(`Brand "${brand.name}" creato`);
          setDialogOpen(false);
          setName("");
          setPositioning("");
          setLastBrandId(brand.id);
          navigate(`/brands/${brand.id}/plans`);
        },
        onError: (err) => toast.error(`Errore: ${err.message}`),
      }
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Tutti i brand gestiti dall'agenzia
          </p>
        </div>
        <Button size="lg" onClick={() => setDialogOpen(true)}>
          <Plus className="h-4 w-4" />
          Nuovo brand
        </Button>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-44 w-full" />
          ))}
        </div>
      ) : (brands ?? []).length === 0 ? (
        <EmptyState
          icon={Store}
          title="Nessun brand"
          description="Crea il primo brand per iniziare a pianificare le email settimanali."
          action={
            <Button onClick={() => setDialogOpen(true)}>
              <Plus className="h-4 w-4" />
              Nuovo brand
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(brands ?? []).map((brand) => (
            <BrandCard key={brand.id} brand={brand} />
          ))}
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nuovo brand</DialogTitle>
            <DialogDescription>
              Crea un nuovo workspace brand. Potrai completare il profilo in
              seguito.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="brand-name">Nome *</Label>
              <Input
                id="brand-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="es. Bergamo Vini"
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="brand-positioning">Positioning</Label>
              <Textarea
                id="brand-positioning"
                value={positioning}
                onChange={(e) => setPositioning(e.target.value)}
                placeholder="Come si posiziona il brand sul mercato (opzionale)"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Annulla
            </Button>
            <Button onClick={handleCreate} disabled={createBrand.isPending}>
              {createBrand.isPending ? "Creazione…" : "Crea brand"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
