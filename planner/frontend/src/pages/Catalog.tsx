import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  CalendarHeart,
  Loader2,
  Package,
  Pencil,
  Plus,
  Rocket,
  Sparkles,
  Star,
  Tag,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/domain/EmptyState";
import {
  useBrand,
  useCreateLaunch,
  useCreateOccasion,
  useCreateOffer,
  useCreateProduct,
  useDeleteLaunch,
  useDeleteOccasion,
  useDeleteOffer,
  useDeleteProduct,
  useLaunches,
  useOccasions,
  useOffers,
  useProducts,
  useSuggestOccasions,
  useUpdateLaunch,
  useUpdateOccasion,
  useUpdateOffer,
  useUpdateProduct,
} from "@/lib/queries";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { Launch, LaunchKind, Occasion, Offer, Product } from "@/types/api";

// -------------------- Prodotti

interface ProductForm {
  name: string;
  category: string;
  price: string;
  seasonality: string;
  is_best_seller: boolean;
  url: string;
  notes: string;
}

const EMPTY_PRODUCT: ProductForm = {
  name: "",
  category: "",
  price: "",
  seasonality: "",
  is_best_seller: false,
  url: "",
  notes: "",
};

function ProductsTab({ brandId }: { brandId: number }) {
  const { data: products, isLoading } = useProducts(brandId);
  const createProduct = useCreateProduct(brandId);
  const updateProduct = useUpdateProduct(brandId);
  const deleteProduct = useDeleteProduct(brandId);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const [form, setForm] = useState<ProductForm>(EMPTY_PRODUCT);

  function openCreate() {
    setEditing(null);
    setForm(EMPTY_PRODUCT);
    setDialogOpen(true);
  }

  function openEdit(product: Product) {
    setEditing(product);
    setForm({
      name: product.name,
      category: product.category ?? "",
      price: product.price != null ? String(product.price) : "",
      seasonality: product.seasonality ?? "",
      is_best_seller: product.is_best_seller,
      url: product.url ?? "",
      notes: product.notes ?? "",
    });
    setDialogOpen(true);
  }

  function handleSubmit() {
    if (!form.name.trim()) {
      toast.error("Il nome del prodotto è obbligatorio");
      return;
    }
    const payload = {
      name: form.name.trim(),
      category: form.category,
      price: form.price === "" ? null : Number(form.price),
      seasonality: form.seasonality,
      is_best_seller: form.is_best_seller,
      url: form.url,
      notes: form.notes,
    };
    const opts = {
      onSuccess: () => {
        toast.success(editing ? "Prodotto aggiornato" : "Prodotto aggiunto");
        setDialogOpen(false);
      },
      onError: (err: Error) => toast.error(`Errore: ${err.message}`),
    };
    if (editing) {
      updateProduct.mutate({ id: editing.id, data: payload }, opts);
    } else {
      createProduct.mutate(payload, opts);
    }
  }

  if (isLoading) return <Skeleton className="h-64 w-full" />;

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" />
          Aggiungi prodotto
        </Button>
      </div>

      {(products ?? []).length === 0 ? (
        <EmptyState
          icon={Package}
          title="Nessun prodotto"
          description="Aggiungi i prodotti del brand: Claude li userà per proporre le email giuste."
          action={
            <Button onClick={openCreate}>
              <Plus className="h-4 w-4" />
              Aggiungi prodotto
            </Button>
          }
        />
      ) : (
        <div className="rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>Categoria</TableHead>
                <TableHead>Prezzo</TableHead>
                <TableHead>Stagionalità</TableHead>
                <TableHead>Best seller</TableHead>
                <TableHead className="w-[90px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(products ?? []).map((product) => (
                <TableRow key={product.id}>
                  <TableCell className="font-medium">{product.name}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {product.category || "—"}
                  </TableCell>
                  <TableCell>{formatCurrency(product.price)}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {product.seasonality || "—"}
                  </TableCell>
                  <TableCell>
                    {product.is_best_seller && (
                      <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="Modifica prodotto"
                        onClick={() => openEdit(product)}
                      >
                        <Pencil className="h-4 w-4 text-muted-foreground" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="Elimina prodotto"
                        onClick={() => {
                          if (window.confirm(`Eliminare "${product.name}"?`)) {
                            deleteProduct.mutate(product.id, {
                              onSuccess: () =>
                                toast.success("Prodotto eliminato"),
                              onError: (err) =>
                                toast.error(`Errore: ${err.message}`),
                            });
                          }
                        }}
                      >
                        <Trash2 className="h-4 w-4 text-muted-foreground" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editing ? "Modifica prodotto" : "Nuovo prodotto"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Nome *</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                autoFocus
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Categoria</Label>
                <Input
                  value={form.category}
                  onChange={(e) =>
                    setForm({ ...form, category: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label>Prezzo (€)</Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={form.price}
                  onChange={(e) => setForm({ ...form, price: e.target.value })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Stagionalità</Label>
              <Input
                value={form.seasonality}
                onChange={(e) =>
                  setForm({ ...form, seasonality: e.target.value })
                }
                placeholder="es. autunno-inverno"
              />
            </div>
            <div className="space-y-2">
              <Label>URL prodotto</Label>
              <Input
                value={form.url}
                onChange={(e) => setForm({ ...form, url: e.target.value })}
                placeholder="https://…"
              />
            </div>
            <div className="space-y-2">
              <Label>Note</Label>
              <Textarea
                rows={2}
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </div>
            <label className="flex items-center gap-2 text-sm font-medium">
              <Checkbox
                checked={form.is_best_seller}
                onCheckedChange={(checked) =>
                  setForm({ ...form, is_best_seller: checked === true })
                }
              />
              Best seller
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Annulla
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={createProduct.isPending || updateProduct.isPending}
            >
              {editing ? "Salva modifiche" : "Aggiungi"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// -------------------- Offerte

interface OfferForm {
  name: string;
  code: string;
  discount: string;
  valid_from: string;
  valid_to: string;
  active: boolean;
  notes: string;
}

const EMPTY_OFFER: OfferForm = {
  name: "",
  code: "",
  discount: "",
  valid_from: "",
  valid_to: "",
  active: true,
  notes: "",
};

function OffersTab({ brandId }: { brandId: number }) {
  const { data: offers, isLoading } = useOffers(brandId);
  const createOffer = useCreateOffer(brandId);
  const updateOffer = useUpdateOffer(brandId);
  const deleteOffer = useDeleteOffer(brandId);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Offer | null>(null);
  const [form, setForm] = useState<OfferForm>(EMPTY_OFFER);

  function openCreate() {
    setEditing(null);
    setForm(EMPTY_OFFER);
    setDialogOpen(true);
  }

  function openEdit(offer: Offer) {
    setEditing(offer);
    setForm({
      name: offer.name,
      code: offer.code ?? "",
      discount: offer.discount ?? "",
      valid_from: offer.valid_from ?? "",
      valid_to: offer.valid_to ?? "",
      active: offer.active,
      notes: offer.notes ?? "",
    });
    setDialogOpen(true);
  }

  function handleSubmit() {
    if (!form.name.trim()) {
      toast.error("Il nome dell'offerta è obbligatorio");
      return;
    }
    const payload = {
      name: form.name.trim(),
      code: form.code,
      discount: form.discount,
      valid_from: form.valid_from || null,
      valid_to: form.valid_to || null,
      active: form.active,
      notes: form.notes,
    };
    const opts = {
      onSuccess: () => {
        toast.success(editing ? "Offerta aggiornata" : "Offerta aggiunta");
        setDialogOpen(false);
      },
      onError: (err: Error) => toast.error(`Errore: ${err.message}`),
    };
    if (editing) {
      updateOffer.mutate({ id: editing.id, data: payload }, opts);
    } else {
      createOffer.mutate(payload, opts);
    }
  }

  if (isLoading) return <Skeleton className="h-64 w-full" />;

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" />
          Aggiungi offerta
        </Button>
      </div>

      {(offers ?? []).length === 0 ? (
        <EmptyState
          icon={Tag}
          title="Nessuna offerta"
          description="Aggiungi offerte e codici sconto da usare nelle email promozionali."
          action={
            <Button onClick={openCreate}>
              <Plus className="h-4 w-4" />
              Aggiungi offerta
            </Button>
          }
        />
      ) : (
        <div className="rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>Codice</TableHead>
                <TableHead>Sconto</TableHead>
                <TableHead>Validità</TableHead>
                <TableHead>Attiva</TableHead>
                <TableHead className="w-[90px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(offers ?? []).map((offer) => (
                <TableRow key={offer.id}>
                  <TableCell className="font-medium">{offer.name}</TableCell>
                  <TableCell>
                    {offer.code ? (
                      <code className="rounded bg-muted px-1.5 py-0.5 text-xs">
                        {offer.code}
                      </code>
                    ) : (
                      "—"
                    )}
                  </TableCell>
                  <TableCell>{offer.discount || "—"}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {offer.valid_from || offer.valid_to
                      ? `${formatDate(offer.valid_from)} → ${formatDate(offer.valid_to)}`
                      : "—"}
                  </TableCell>
                  <TableCell>
                    <Switch
                      checked={offer.active}
                      aria-label="Offerta attiva"
                      onCheckedChange={(checked) =>
                        updateOffer.mutate(
                          { id: offer.id, data: { active: checked } },
                          {
                            onSuccess: () =>
                              toast.success(
                                checked
                                  ? "Offerta attivata"
                                  : "Offerta disattivata"
                              ),
                            onError: (err) =>
                              toast.error(`Errore: ${err.message}`),
                          }
                        )
                      }
                    />
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="Modifica offerta"
                        onClick={() => openEdit(offer)}
                      >
                        <Pencil className="h-4 w-4 text-muted-foreground" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="Elimina offerta"
                        onClick={() => {
                          if (window.confirm(`Eliminare "${offer.name}"?`)) {
                            deleteOffer.mutate(offer.id, {
                              onSuccess: () =>
                                toast.success("Offerta eliminata"),
                              onError: (err) =>
                                toast.error(`Errore: ${err.message}`),
                            });
                          }
                        }}
                      >
                        <Trash2 className="h-4 w-4 text-muted-foreground" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editing ? "Modifica offerta" : "Nuova offerta"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Nome *</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                autoFocus
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Codice sconto</Label>
                <Input
                  value={form.code}
                  onChange={(e) => setForm({ ...form, code: e.target.value })}
                  placeholder="es. GIUGNO20"
                />
              </div>
              <div className="space-y-2">
                <Label>Sconto</Label>
                <Input
                  value={form.discount}
                  onChange={(e) =>
                    setForm({ ...form, discount: e.target.value })
                  }
                  placeholder="es. -20%"
                />
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Valida dal</Label>
                <Input
                  type="date"
                  value={form.valid_from}
                  onChange={(e) =>
                    setForm({ ...form, valid_from: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label>Valida fino al</Label>
                <Input
                  type="date"
                  value={form.valid_to}
                  onChange={(e) =>
                    setForm({ ...form, valid_to: e.target.value })
                  }
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Note</Label>
              <Textarea
                rows={2}
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </div>
            <label className="flex items-center gap-2 text-sm font-medium">
              <Switch
                checked={form.active}
                onCheckedChange={(checked) =>
                  setForm({ ...form, active: checked })
                }
              />
              Offerta attiva
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Annulla
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={createOffer.isPending || updateOffer.isPending}
            >
              {editing ? "Salva modifiche" : "Aggiungi"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// -------------------- Occasioni

interface OccasionForm {
  name: string;
  date: string;
  notes: string;
}

const EMPTY_OCCASION: OccasionForm = { name: "", date: "", notes: "" };

function currentMonth(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

const KIND_STYLES: Record<string, string> = {
  festività: "border-rose-200 bg-rose-50 text-rose-700",
  ponte: "border-sky-200 bg-sky-50 text-sky-700",
  ricorrenza: "border-amber-200 bg-amber-50 text-amber-700",
};

function SuggestOccasionsCard({
  brandId,
  existingNames,
}: {
  brandId: number;
  existingNames: Set<string>;
}) {
  const { data: brand } = useBrand(brandId);
  const suggest = useSuggestOccasions(brandId);
  const createOccasion = useCreateOccasion(brandId);
  const [month, setMonth] = useState(currentMonth());
  const [checked, setChecked] = useState<Set<number>>(new Set());

  const suggestions = suggest.data?.suggestions ?? [];

  function handleSuggest() {
    setChecked(new Set());
    suggest.mutate(
      { month },
      {
        onSuccess: (out) => {
          if (out.suggestions.length === 0) {
            toast.info("Nessuna data rilevante trovata per quel mese");
          } else {
            // preseleziona tutte quelle non già presenti a calendario
            setChecked(
              new Set(
                out.suggestions
                  .map((s, i) => (existingNames.has(s.name.toLowerCase()) ? -1 : i))
                  .filter((i) => i >= 0)
              )
            );
          }
        },
        onError: (err) => toast.error(`Analisi fallita: ${err.message}`),
      }
    );
  }

  async function handleAddSelected() {
    const selected = suggestions.filter((_, i) => checked.has(i));
    if (selected.length === 0) {
      toast.error("Seleziona almeno un suggerimento");
      return;
    }
    let done = 0;
    for (const s of selected) {
      await new Promise<void>((resolve) => {
        createOccasion.mutate(
          {
            name: s.name,
            date: s.date,
            notes: `[${s.kind}] ${s.idea}`,
          },
          { onSettled: () => resolve(), onSuccess: () => done++ }
        );
      });
    }
    toast.success(`${done} occasioni aggiunte al calendario`);
    setChecked(new Set());
    suggest.reset();
  }

  return (
    <div className="rounded-xl border border-primary/25 bg-gradient-to-br from-primary/[0.04] to-transparent p-4">
      <div className="flex items-center gap-2 font-medium">
        <Sparkles className="h-4 w-4 text-primary" />
        Suggerisci date dal calendario del paese
      </div>
      <p className="mt-1 text-sm text-muted-foreground">
        Analizza festività, ponti e ricorrenze rilevanti in{" "}
        {brand?.country || "IT"} e propone idee email da inserire a calendario.
        Il paese si imposta nel Profilo brand.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Input
          type="month"
          className="w-44"
          value={month}
          onChange={(e) => setMonth(e.target.value)}
          aria-label="Mese da analizzare"
        />
        <Button onClick={handleSuggest} disabled={suggest.isPending || !month}>
          {suggest.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="h-4 w-4" />
          )}
          {suggest.isPending ? "Analisi…" : "Suggerisci date"}
        </Button>
      </div>

      {suggestions.length > 0 && (
        <div className="mt-4 space-y-2">
          {suggestions.map((s, i) => {
            const already = existingNames.has(s.name.toLowerCase());
            return (
              <label
                key={`${s.date}-${s.name}`}
                className={`flex cursor-pointer items-start gap-3 rounded-lg border border-border bg-card px-3 py-2.5 ${
                  already ? "opacity-60" : ""
                }`}
              >
                <Checkbox
                  className="mt-0.5"
                  checked={checked.has(i)}
                  disabled={already}
                  onCheckedChange={(v) =>
                    setChecked((prev) => {
                      const next = new Set(prev);
                      if (v) next.add(i);
                      else next.delete(i);
                      return next;
                    })
                  }
                />
                <div className="min-w-0 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{s.name}</span>
                    <span className="text-xs text-muted-foreground">
                      {formatDate(s.date)}
                    </span>
                    <span
                      className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${
                        KIND_STYLES[s.kind] ?? "border-border bg-muted text-muted-foreground"
                      }`}
                    >
                      {s.kind}
                    </span>
                    {already && (
                      <span className="text-[11px] text-muted-foreground">
                        già a calendario
                      </span>
                    )}
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground">{s.idea}</p>
                </div>
              </label>
            );
          })}
          <div className="flex justify-end pt-1">
            <Button onClick={handleAddSelected} disabled={createOccasion.isPending}>
              <Plus className="h-4 w-4" />
              Aggiungi selezionate ({checked.size})
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function OccasionsTab({ brandId }: { brandId: number }) {
  const { data: occasions, isLoading } = useOccasions(brandId);
  const createOccasion = useCreateOccasion(brandId);
  const updateOccasion = useUpdateOccasion(brandId);
  const deleteOccasion = useDeleteOccasion(brandId);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Occasion | null>(null);
  const [form, setForm] = useState<OccasionForm>(EMPTY_OCCASION);

  const existingNames = new Set(
    (occasions ?? []).map((o) => o.name.toLowerCase())
  );

  function openCreate() {
    setEditing(null);
    setForm(EMPTY_OCCASION);
    setDialogOpen(true);
  }

  function openEdit(occasion: Occasion) {
    setEditing(occasion);
    setForm({
      name: occasion.name,
      date: occasion.date ?? "",
      notes: occasion.notes ?? "",
    });
    setDialogOpen(true);
  }

  function handleSubmit() {
    if (!form.name.trim()) {
      toast.error("Il nome dell'occasione è obbligatorio");
      return;
    }
    const payload = {
      name: form.name.trim(),
      date: form.date || null,
      notes: form.notes,
    };
    const opts = {
      onSuccess: () => {
        toast.success(editing ? "Occasione aggiornata" : "Occasione aggiunta");
        setDialogOpen(false);
      },
      onError: (err: Error) => toast.error(`Errore: ${err.message}`),
    };
    if (editing) {
      updateOccasion.mutate({ id: editing.id, data: payload }, opts);
    } else {
      createOccasion.mutate(payload, opts);
    }
  }

  if (isLoading) return <Skeleton className="h-64 w-full" />;

  return (
    <div className="space-y-4">
      <SuggestOccasionsCard brandId={brandId} existingNames={existingNames} />

      <div className="flex justify-end">
        <Button variant="outline" onClick={openCreate}>
          <Plus className="h-4 w-4" />
          Aggiungi occasione
        </Button>
      </div>

      {(occasions ?? []).length === 0 ? (
        <EmptyState
          icon={CalendarHeart}
          title="Nessuna occasione"
          description="Aggiungi ricorrenze e temi del periodo (festività, eventi, stagionalità) da sfruttare nei piani."
          action={
            <Button onClick={openCreate}>
              <Plus className="h-4 w-4" />
              Aggiungi occasione
            </Button>
          }
        />
      ) : (
        <div className="space-y-2">
          {(occasions ?? []).map((occasion) => (
            <div
              key={occasion.id}
              className="flex items-center justify-between rounded-lg border border-border bg-card px-4 py-3"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{occasion.name}</span>
                  {occasion.date && (
                    <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                      {formatDate(occasion.date)}
                    </span>
                  )}
                </div>
                {occasion.notes && (
                  <p className="mt-0.5 truncate text-xs text-muted-foreground">
                    {occasion.notes}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Modifica occasione"
                  onClick={() => openEdit(occasion)}
                >
                  <Pencil className="h-4 w-4 text-muted-foreground" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Elimina occasione"
                  onClick={() => {
                    if (window.confirm(`Eliminare "${occasion.name}"?`)) {
                      deleteOccasion.mutate(occasion.id, {
                        onSuccess: () => toast.success("Occasione eliminata"),
                        onError: (err) => toast.error(`Errore: ${err.message}`),
                      });
                    }
                  }}
                >
                  <Trash2 className="h-4 w-4 text-muted-foreground" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editing ? "Modifica occasione" : "Nuova occasione"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Nome *</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="es. Ferragosto"
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <Label>Data</Label>
              <Input
                type="date"
                value={form.date}
                onChange={(e) => setForm({ ...form, date: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Note</Label>
              <Textarea
                rows={2}
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                placeholder="es. grigliate, vini freschi"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Annulla
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={createOccasion.isPending || updateOccasion.isPending}
            >
              {editing ? "Salva modifiche" : "Aggiungi"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// -------------------- Lanci & Promo

interface LaunchForm {
  name: string;
  kind: LaunchKind;
  start_date: string;
  end_date: string;
  subject: string;
  notes: string;
  active: boolean;
}

const EMPTY_LAUNCH: LaunchForm = {
  name: "",
  kind: "promo",
  start_date: "",
  end_date: "",
  subject: "",
  notes: "",
  active: true,
};

const LAUNCH_KIND_STYLES: Record<string, string> = {
  lancio: "border-indigo-200 bg-indigo-50 text-indigo-700",
  promo: "border-amber-200 bg-amber-50 text-amber-700",
};

function launchDuration(l: Launch): string {
  if (!l.start_date || !l.end_date) return "—";
  const days =
    Math.round(
      (new Date(l.end_date).getTime() - new Date(l.start_date).getTime()) /
        86_400_000
    ) + 1;
  if (days <= 0) return "—";
  if (days === 1) return "24h flash";
  if (days === 2) return "48h flash";
  return `${days} giorni`;
}

function LaunchesTab({ brandId }: { brandId: number }) {
  const { data: launches, isLoading } = useLaunches(brandId);
  const createLaunch = useCreateLaunch(brandId);
  const updateLaunch = useUpdateLaunch(brandId);
  const deleteLaunch = useDeleteLaunch(brandId);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Launch | null>(null);
  const [form, setForm] = useState<LaunchForm>(EMPTY_LAUNCH);

  function openCreate() {
    setEditing(null);
    setForm(EMPTY_LAUNCH);
    setDialogOpen(true);
  }

  function openEdit(launch: Launch) {
    setEditing(launch);
    setForm({
      name: launch.name,
      kind: launch.kind,
      start_date: launch.start_date ?? "",
      end_date: launch.end_date ?? "",
      subject: launch.subject ?? "",
      notes: launch.notes ?? "",
      active: launch.active,
    });
    setDialogOpen(true);
  }

  function handleSubmit() {
    if (!form.name.trim()) {
      toast.error("Il nome del lancio/promo è obbligatorio");
      return;
    }
    const payload = {
      name: form.name.trim(),
      kind: form.kind,
      start_date: form.start_date,
      end_date: form.end_date,
      subject: form.subject,
      notes: form.notes,
      active: form.active,
    };
    const opts = {
      onSuccess: () => {
        toast.success(editing ? "Aggiornato" : "Aggiunto: entrerà nel prossimo piano come sequenza dedicata");
        setDialogOpen(false);
      },
      onError: (err: Error) => toast.error(`Errore: ${err.message}`),
    };
    if (editing) {
      updateLaunch.mutate({ id: editing.id, data: payload }, opts);
    } else {
      createLaunch.mutate(payload, opts);
    }
  }

  if (isLoading) return <Skeleton className="h-64 w-full" />;

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-primary/25 bg-gradient-to-br from-primary/[0.04] to-transparent p-4 text-sm">
        <div className="flex items-center gap-2 font-medium">
          <Rocket className="h-4 w-4 text-primary" />
          Come funziona
        </div>
        <p className="mt-1 text-muted-foreground">
          Ogni lancio o promo inserito qui diventa una <strong>sequenza email
          coordinata</strong> nel piano del mese: hype/teaser, annuncio, follow-up,
          last call e final reminder secondo la durata (5-7 giorni = funnel completo,
          3 giorni = senza follow-up, flash 24/48h = solo le email essenziali).
          Nel piano trovi la strategia spiegata e le proposte extra.
        </p>
      </div>

      <div className="flex justify-end">
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" />
          Aggiungi lancio / promo
        </Button>
      </div>

      {(launches ?? []).length === 0 ? (
        <EmptyState
          icon={Rocket}
          title="Nessun lancio o promo"
          description="Aggiungi un lancio prodotto o una promo con le date: il prossimo piano preparerà la sequenza email dedicata."
          action={
            <Button onClick={openCreate}>
              <Plus className="h-4 w-4" />
              Aggiungi lancio / promo
            </Button>
          }
        />
      ) : (
        <div className="rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Durata</TableHead>
                <TableHead>Protagonista</TableHead>
                <TableHead>Attivo</TableHead>
                <TableHead className="w-[90px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(launches ?? []).map((launch) => (
                <TableRow key={launch.id}>
                  <TableCell className="font-medium">{launch.name}</TableCell>
                  <TableCell>
                    <span
                      className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${
                        LAUNCH_KIND_STYLES[launch.kind] ??
                        "border-border bg-muted text-muted-foreground"
                      }`}
                    >
                      {launch.kind}
                    </span>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {launch.start_date || launch.end_date
                      ? `${formatDate(launch.start_date)} → ${formatDate(launch.end_date)}`
                      : "—"}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {launchDuration(launch)}
                  </TableCell>
                  <TableCell className="max-w-[180px] truncate text-sm text-muted-foreground">
                    {launch.subject || "—"}
                  </TableCell>
                  <TableCell>
                    <Switch
                      checked={launch.active}
                      aria-label="Lancio attivo"
                      onCheckedChange={(checked) =>
                        updateLaunch.mutate(
                          { id: launch.id, data: { active: checked } },
                          {
                            onSuccess: () =>
                              toast.success(checked ? "Attivato" : "Disattivato"),
                            onError: (err) =>
                              toast.error(`Errore: ${err.message}`),
                          }
                        )
                      }
                    />
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="Modifica lancio"
                        onClick={() => openEdit(launch)}
                      >
                        <Pencil className="h-4 w-4 text-muted-foreground" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="Elimina lancio"
                        onClick={() => {
                          if (window.confirm(`Eliminare "${launch.name}"?`)) {
                            deleteLaunch.mutate(launch.id, {
                              onSuccess: () => toast.success("Eliminato"),
                              onError: (err) =>
                                toast.error(`Errore: ${err.message}`),
                            });
                          }
                        }}
                      >
                        <Trash2 className="h-4 w-4 text-muted-foreground" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editing ? "Modifica lancio / promo" : "Nuovo lancio / promo"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Nome *</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="es. Summer Sale, Lancio Crema Viso"
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <Label>Tipo</Label>
              <div className="flex gap-2">
                {(["promo", "lancio"] as LaunchKind[]).map((k) => (
                  <Button
                    key={k}
                    type="button"
                    variant={form.kind === k ? "default" : "outline"}
                    size="sm"
                    onClick={() => setForm({ ...form, kind: k })}
                  >
                    {k === "promo" ? "Promo / sale" : "Lancio prodotto"}
                  </Button>
                ))}
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>{form.kind === "promo" ? "Inizio sale" : "Giorno del lancio"}</Label>
                <Input
                  type="date"
                  value={form.start_date}
                  onChange={(e) =>
                    setForm({ ...form, start_date: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label>{form.kind === "promo" ? "Fine sale" : "Fine offerta lancio (opzionale)"}</Label>
                <Input
                  type="date"
                  value={form.end_date}
                  onChange={(e) =>
                    setForm({ ...form, end_date: e.target.value })
                  }
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Prodotto / offerta protagonista</Label>
              <Input
                value={form.subject}
                onChange={(e) => setForm({ ...form, subject: e.target.value })}
                placeholder="es. Kit Estate, -20% su tutto"
              />
            </div>
            <div className="space-y-2">
              <Label>Note per la strategia</Label>
              <Textarea
                rows={2}
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                placeholder="es. non rivelare lo sconto prima del via, target VIP…"
              />
            </div>
            <label className="flex items-center gap-2 text-sm font-medium">
              <Switch
                checked={form.active}
                onCheckedChange={(checked) =>
                  setForm({ ...form, active: checked })
                }
              />
              Attivo (incluso nei prossimi piani)
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Annulla
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={createLaunch.isPending || updateLaunch.isPending}
            >
              {editing ? "Salva modifiche" : "Aggiungi"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// -------------------- Pagina

export function Catalog() {
  const { brandId: brandIdParam } = useParams();
  const brandId = Number(brandIdParam);

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">Catalogo</h1>
        <p className="text-sm text-muted-foreground">
          Prodotti, offerte, occasioni e lanci/promo usati nella generazione dei piani.
        </p>
      </div>

      <Tabs defaultValue="products">
        <TabsList>
          <TabsTrigger value="products">Prodotti</TabsTrigger>
          <TabsTrigger value="offers">Offerte</TabsTrigger>
          <TabsTrigger value="occasions">Occasioni</TabsTrigger>
          <TabsTrigger value="launches">Lanci &amp; Promo</TabsTrigger>
        </TabsList>
        <TabsContent value="products" className="pt-4">
          <ProductsTab brandId={brandId} />
        </TabsContent>
        <TabsContent value="offers" className="pt-4">
          <OffersTab brandId={brandId} />
        </TabsContent>
        <TabsContent value="occasions" className="pt-4">
          <OccasionsTab brandId={brandId} />
        </TabsContent>
        <TabsContent value="launches" className="pt-4">
          <LaunchesTab brandId={brandId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
