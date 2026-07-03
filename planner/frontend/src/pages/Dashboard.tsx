import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  Loader2,
  Package,
  Plus,
  Store,
  Tag,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { apiUpload } from "@/lib/api";
import { keys } from "@/lib/queries";
import type { ExtractedProfile } from "@/types/api";
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
import { formatMonth } from "@/lib/utils";
import type { BrandSummary } from "@/types/api";

/* Gradiente deterministico per l'avatar del brand */
const AVATAR_GRADIENTS = [
  "from-indigo-500 to-violet-600",
  "from-amber-500 to-orange-600",
  "from-emerald-500 to-teal-600",
  "from-rose-500 to-pink-600",
  "from-sky-500 to-blue-600",
  "from-fuchsia-500 to-purple-600",
];

function brandInitials(name: string): string {
  const words = name.trim().split(/\s+/);
  return (words.length >= 2 ? words[0][0] + words[1][0] : name.slice(0, 2))
    .toUpperCase();
}

function BrandCard({ brand }: { brand: BrandSummary }) {
  const navigate = useNavigate();
  const gradient = AVATAR_GRADIENTS[brand.id % AVATAR_GRADIENTS.length];

  return (
    <Card
      role="button"
      tabIndex={0}
      className="card-lift group cursor-pointer overflow-hidden border-border/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
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
          <div className="flex items-center gap-3">
            <div
              aria-hidden
              className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${gradient} font-display text-sm font-semibold text-white shadow-sm`}
            >
              {brandInitials(brand.name)}
            </div>
            <div>
              <CardTitle className="font-display text-base tracking-tight transition-colors group-hover:text-primary">
                {brand.name}
              </CardTitle>
              <p className="line-clamp-1 text-xs text-muted-foreground">
                {brand.positioning || "Nessun positioning definito"}
              </p>
            </div>
          </div>
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
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-lg bg-muted/60 px-3 py-2">
            <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
              <Package className="h-3 w-3" />
              Prodotti
            </div>
            <div className="mt-0.5 text-sm font-semibold tabular-nums">
              {brand.num_products}
            </div>
          </div>
          <div className="rounded-lg bg-muted/60 px-3 py-2">
            <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
              <Tag className="h-3 w-3" />
              Offerte attive
            </div>
            <div className="mt-0.5 text-sm font-semibold tabular-nums">
              {brand.num_active_offers}
            </div>
          </div>
        </div>
        <div className="flex items-center justify-between border-t border-border/60 pt-3">
          <span className="text-xs text-muted-foreground">
            Ultimo piano
            {brand.last_plan_month_start
              ? ` · ${formatMonth(brand.last_plan_month_start)}`
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

  const qc = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [name, setName] = useState("");
  const [positioning, setPositioning] = useState("");
  const [brandFiles, setBrandFiles] = useState<File[]>([]);
  const [extracting, setExtracting] = useState(false);

  // Il BrandSwitcher può chiedere di aprire il dialog via location state.
  useEffect(() => {
    if ((location.state as { openNewBrand?: boolean } | null)?.openNewBrand) {
      setDialogOpen(true);
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [location.state, location.pathname, navigate]);

  async function extractFromFiles(brandId: number): Promise<void> {
    const fd = new FormData();
    for (const f of brandFiles) fd.append("files", f);
    setExtracting(true);
    try {
      const result = await apiUpload<ExtractedProfile>(
        `/brands/${brandId}/extract-profile`,
        fd,
        { apply: "true" }
      );
      qc.invalidateQueries({ queryKey: keys.brand(brandId) });
      qc.invalidateQueries({ queryKey: keys.brands });
      qc.invalidateQueries({ queryKey: keys.products(brandId) });
      const extra =
        result.products_created > 0
          ? ` (+${result.products_created} prodotti importati)`
          : "";
      toast.success(`Profilo compilato dal documento${extra}: rivedilo e salva`, {
        duration: 6000,
      });
    } catch (err) {
      toast.error(
        `Brand creato, ma estrazione fallita: ${err instanceof Error ? err.message : err}`
      );
    } finally {
      setExtracting(false);
    }
  }

  function handleCreate() {
    const trimmed = name.trim();
    if (!trimmed) {
      toast.error("Il nome del brand è obbligatorio");
      return;
    }
    createBrand.mutate(
      { name: trimmed, positioning: positioning.trim() || undefined },
      {
        onSuccess: async (brand) => {
          toast.success(`Brand "${brand.name}" creato`);
          setLastBrandId(brand.id);
          const hasFiles = brandFiles.length > 0;
          if (hasFiles) {
            await extractFromFiles(brand.id);
          }
          setDialogOpen(false);
          setName("");
          setPositioning("");
          setBrandFiles([]);
          navigate(
            hasFiles ? `/brands/${brand.id}/profile` : `/brands/${brand.id}/plans`
          );
        },
        onError: (err) => toast.error(`Errore: ${err.message}`),
      }
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">
            I tuoi clienti
          </p>
          <h1 className="font-display mt-1 text-3xl font-semibold tracking-tight">
            Il piano della settimana,{" "}
            <em className="text-primary">per ogni brand</em>
          </h1>
          <p className="mt-1.5 text-sm text-muted-foreground">
            Scegli un workspace o creane uno nuovo per iniziare a pianificare.
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
            <div className="space-y-2">
              <Label htmlFor="brand-files">
                Brand book / questionario (opzionale)
              </Label>
              <Input
                id="brand-files"
                type="file"
                accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown"
                multiple
                className="cursor-pointer"
                onChange={(e) =>
                  setBrandFiles(Array.from(e.target.files ?? []).slice(0, 3))
                }
              />
              <p className="text-xs text-muted-foreground">
                Carica il PDF del cliente e l'AI compila da sola profilo, tono
                di voce e avatar (fino a 3 file, max 20 MB).
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDialogOpen(false)}
              disabled={extracting}
            >
              Annulla
            </Button>
            <Button
              onClick={handleCreate}
              disabled={createBrand.isPending || extracting}
            >
              {extracting && <Loader2 className="h-4 w-4 animate-spin" />}
              {extracting
                ? "Analisi documento… (~1 min)"
                : createBrand.isPending
                  ? "Creazione…"
                  : "Crea brand"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
