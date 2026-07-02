import { useEffect, useState } from "react";
import {
  ExternalLink,
  Loader2,
  RefreshCw,
  Search,
  SwatchBook,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
  useSyncTemplates,
  useTemplateCategories,
  useTemplates,
} from "@/lib/queries";

const ALL_CATEGORIES = "__all__";

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
          <h1 className="text-2xl font-semibold tracking-tight">
            Template Canva
          </h1>
          <p className="text-sm text-muted-foreground">
            Libreria letta dal database Notion dell'agenzia.
          </p>
        </div>
        <Button onClick={handleSync} disabled={syncTemplates.isPending}>
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
              : 'La libreria è vuota: premi "Sincronizza da Notion" per importare i template.'
          }
          action={
            !search && !effectiveCategory ? (
              <Button onClick={handleSync} disabled={syncTemplates.isPending}>
                <RefreshCw className="h-4 w-4" />
                Sincronizza da Notion
              </Button>
            ) : undefined
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
