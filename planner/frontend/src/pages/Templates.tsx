import { useEffect, useState } from "react";
import {
  ExternalLink,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  SwatchBook,
  Trash2,
  Wand2,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/domain/EmptyState";
import {
  useCanvaSet,
  useSaveCanvaSet,
  useSyncTemplates,
  useTemplateCategories,
  useTemplates,
} from "@/lib/queries";

const ALL_CATEGORIES = "__all__";

interface RangeDraft {
  category: string;
  start: string;
  end: string;
}

function CanvaSetCard() {
  const { data: canvaSet, isLoading } = useCanvaSet();
  const saveSet = useSaveCanvaSet();

  const [fileUrl, setFileUrl] = useState("");
  const [ranges, setRanges] = useState<RangeDraft[]>([]);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    if (canvaSet && !initialized) {
      setFileUrl(canvaSet.canva_file_url);
      setRanges(
        canvaSet.ranges.length > 0
          ? canvaSet.ranges.map((r) => ({
              category: r.category,
              start: String(r.start),
              end: String(r.end),
            }))
          : [{ category: "", start: "", end: "" }]
      );
      setInitialized(true);
    }
  }, [canvaSet, initialized]);

  function updateRange(index: number, patch: Partial<RangeDraft>) {
    setRanges((rows) =>
      rows.map((row, i) => (i === index ? { ...row, ...patch } : row))
    );
  }

  function handleSave() {
    const payload = {
      canva_file_url: fileUrl.trim(),
      ranges: ranges
        .filter((r) => r.category.trim() || r.start || r.end)
        .map((r) => ({
          category: r.category.trim(),
          start: parseInt(r.start, 10) || 0,
          end: parseInt(r.end, 10) || 0,
        })),
    };
    saveSet.mutate(payload, {
      onSuccess: (set) => {
        toast.success(
          `Libreria generata: ${set.template_count} template in ${set.ranges.length} categorie`
        );
      },
      onError: (err) => toast.error(err.message),
    });
  }

  if (isLoading) {
    return <Skeleton className="h-48 w-full" />;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>File Canva unico</CardTitle>
        <CardDescription>
          Un solo file Canva con i template numerati (una pagina per template).
          Assegna le categorie per intervalli di numeri — es. 1–5 promo, 7–21
          educative — come nella pagina Notion dell'agenzia: in base al tipo di
          email il piano suggerirà il numero di template giusto.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="canva-file-url">Link del file Canva</Label>
          <Input
            id="canva-file-url"
            placeholder="https://www.canva.com/design/…/edit"
            value={fileUrl}
            onChange={(e) => setFileUrl(e.target.value)}
          />
        </div>

        <div className="space-y-2">
          <Label>Intervalli per categoria</Label>
          <div className="space-y-2">
            {ranges.map((row, i) => (
              <div key={i} className="flex items-center gap-2">
                <Input
                  className="flex-1"
                  placeholder="Categoria (es. promo, educativa)"
                  value={row.category}
                  onChange={(e) => updateRange(i, { category: e.target.value })}
                />
                <Input
                  className="w-24"
                  type="number"
                  min={1}
                  placeholder="Da n."
                  value={row.start}
                  onChange={(e) => updateRange(i, { start: e.target.value })}
                />
                <Input
                  className="w-24"
                  type="number"
                  min={1}
                  placeholder="A n."
                  value={row.end}
                  onChange={(e) => updateRange(i, { end: e.target.value })}
                />
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Rimuovi intervallo"
                  disabled={ranges.length === 1}
                  onClick={() =>
                    setRanges((rows) => rows.filter((_, j) => j !== i))
                  }
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              setRanges((rows) => [...rows, { category: "", start: "", end: "" }])
            }
          >
            <Plus className="h-4 w-4" />
            Aggiungi intervallo
          </Button>
        </div>

        <div className="flex items-center justify-between pt-1">
          <p className="text-xs text-muted-foreground">
            {canvaSet && canvaSet.template_count > 0
              ? `Libreria attuale dal set: ${canvaSet.template_count} template`
              : "Nessun set applicato"}
          </p>
          <Button onClick={handleSave} disabled={saveSet.isPending}>
            {saveSet.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Wand2 className="h-4 w-4" />
            )}
            {saveSet.isPending ? "Salvataggio…" : "Salva e genera libreria"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export function Templates() {
  const [category, setCategory] = useState<string>(ALL_CATEGORIES);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  // Debounce della ricerca per non interrogare l'API a ogni battuta.
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search.trim()), 300);
    return () => clearTimeout(t);
  }, [search]);

  const effectiveCategory =
    category === ALL_CATEGORIES ? undefined : category;
  const { data: templates, isLoading } = useTemplates(
    effectiveCategory,
    debouncedSearch || undefined
  );
  const { data: categories } = useTemplateCategories();
  const syncTemplates = useSyncTemplates();

  function handleSync() {
    syncTemplates.mutate(undefined, {
      onSuccess: (result) => {
        toast.success(
          `Sincronizzati ${result.synced} template in ${result.categories} categorie`
        );
      },
      onError: (err) => {
        if (err.status === 502) {
          toast.error(`Notion non configurato o non raggiungibile: ${err.message}`);
        } else {
          toast.error(`Errore sincronizzazione: ${err.message}`);
        }
      },
    });
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight">
            Template Canva
          </h1>
          <p className="text-sm text-muted-foreground">
            Libreria dei template: dal file Canva unico numerato, oppure dal
            database Notion.
          </p>
        </div>
        <Button
          variant="outline"
          onClick={handleSync}
          disabled={syncTemplates.isPending}
        >
          {syncTemplates.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
          {syncTemplates.isPending
            ? "Sincronizzazione…"
            : "Sincronizza da Notion"}
        </Button>
      </div>

      <CanvaSetCard />

      {/* Filtri */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative min-w-[240px] flex-1 sm:max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            className="pl-8"
            placeholder="Cerca template…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select value={category} onValueChange={setCategory}>
          <SelectTrigger className="w-[220px]">
            <SelectValue placeholder="Categoria" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_CATEGORIES}>Tutte le categorie</SelectItem>
            {(categories ?? []).map((c) => (
              <SelectItem key={c.category} value={c.category}>
                {c.category} ({c.count})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Griglia */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-36 w-full" />
          ))}
        </div>
      ) : (templates ?? []).length === 0 ? (
        <EmptyState
          icon={SwatchBook}
          title="Nessun template"
          description={
            search || effectiveCategory
              ? "Nessun template corrisponde ai filtri. Prova a cambiare ricerca o categoria."
              : "La libreria è vuota: configura il file Canva qui sopra, oppure sincronizza dal database Notion."
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(templates ?? []).map((template) => (
            <Card key={template.id} className="flex flex-col">
              <CardContent className="flex flex-1 flex-col gap-3 p-4">
                <div className="flex items-start justify-between gap-2">
                  <span className="font-medium leading-snug">
                    {template.name}
                  </span>
                  <span className="shrink-0 rounded-full border border-border bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                    {template.category}
                  </span>
                </div>
                {template.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {template.tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded bg-muted px-1.5 py-0.5 text-[11px] text-muted-foreground"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
                <div className="mt-auto pt-2">
                  <Button variant="outline" size="sm" className="w-full" asChild>
                    <a
                      href={template.canva_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      Apri in Canva
                    </a>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
