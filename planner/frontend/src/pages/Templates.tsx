import { useEffect, useState } from "react";
import {
  ExternalLink,
  Image as ImageIcon,
  Loader2,
  RefreshCw,
  Search,
  SwatchBook,
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
import { Textarea } from "@/components/ui/textarea";
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
  useUploadPreviews,
  useSyncTemplates,
  useTemplateCategories,
  useTemplates,
} from "@/lib/queries";

const ALL_CATEGORIES = "__all__";

const ENTRIES_PLACEHOLDER = `About x3
Before & After x3
Flash Sale x3
FAQ x3
How-to? x3
…incolla qui l'elenco dalla pagina Notion (una riga per tipo)`;

/** Parsa "Nome x3" per la preview locale (il backend riparsa comunque). */
function parseEntriesPreview(text: string): { types: number; total: number } {
  let types = 0;
  let total = 0;
  for (const raw of text.split("\n")) {
    const line = raw.trim().replace(/^[-•*]\s*/, "");
    if (!line || line.startsWith("#")) continue;
    const m = line.match(/[xX×]\s*(\d*)\s*$/);
    types += 1;
    total += m && m[1] ? parseInt(m[1], 10) : 3;
  }
  return { types, total };
}

function CanvaSetCard() {
  const { data: canvaSet, isLoading } = useCanvaSet();
  const saveSet = useSaveCanvaSet();
  const uploadPreviews = useUploadPreviews();

  const [fileUrl, setFileUrl] = useState("");
  const [entriesText, setEntriesText] = useState("");
  const [previewFiles, setPreviewFiles] = useState<File[]>([]);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    if (canvaSet && !initialized) {
      setFileUrl(canvaSet.canva_file_url);
      if (canvaSet.entries.length > 0) {
        setEntriesText(
          canvaSet.entries.map((e) => `${e.name} x${e.count}`).join("\n")
        );
      }
      setInitialized(true);
    }
  }, [canvaSet, initialized]);

  const parsed = parseEntriesPreview(entriesText);

  function handleSave() {
    saveSet.mutate(
      { canva_file_url: fileUrl.trim(), entries_text: entriesText },
      {
        onSuccess: (set) => {
          toast.success(
            `Libreria generata: ${set.template_count} template in ${set.categories.length} categorie (assegnate automaticamente)`
          );
        },
        onError: (err) => toast.error(err.message),
      }
    );
  }

  function handleUploadPreviews() {
    if (previewFiles.length === 0) {
      toast.error("Seleziona le immagini esportate da Canva (o uno zip)");
      return;
    }
    uploadPreviews.mutate(previewFiles, {
      onSuccess: (res) => {
        setPreviewFiles([]);
        toast.success(
          `${res.saved} anteprime caricate, ${res.matched} template abbinati`
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
        <CardTitle>Set template Canva</CardTitle>
        <CardDescription>
          Incolla l'elenco dei tipi dalla pagina Notion (es. "About x3"): la
          libreria si genera da sola, con le categorie assegnate
          automaticamente e il link che apre il file Canva direttamente sulla
          pagina giusta.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="canva-file-url">Link del file Canva (opzionale)</Label>
          <Input
            id="canva-file-url"
            placeholder="https://www.canva.com/design/…/edit"
            value={fileUrl}
            onChange={(e) => setFileUrl(e.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            Le pagine del file devono seguire l'ordine dell'elenco: il
            template n. 12 aprirà …/edit#12.
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="entries-text">Elenco tipi (uno per riga)</Label>
          <Textarea
            id="entries-text"
            rows={8}
            className="font-mono text-xs"
            placeholder={ENTRIES_PLACEHOLDER}
            value={entriesText}
            onChange={(e) => setEntriesText(e.target.value)}
          />
        </div>

        <div className="flex items-center justify-between pt-1">
          <p className="text-xs text-muted-foreground">
            {entriesText.trim()
              ? `Nell'elenco: ${parsed.types} tipi → ${parsed.total} template`
              : canvaSet && canvaSet.template_count > 0
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

        <div className="space-y-2 rounded-lg border border-dashed border-border p-3">
          <Label htmlFor="preview-files" className="flex items-center gap-2">
            <ImageIcon className="h-4 w-4 text-muted-foreground" />
            Anteprime dei template
          </Label>
          <p className="text-xs text-muted-foreground">
            Da Canva: Condividi → Scarica → PNG (tutte le pagine). Carica qui
            le immagini numerate o lo zip: vengono abbinate per numero di
            pagina e appaiono nella libreria e nelle card email.
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <Input
              id="preview-files"
              type="file"
              multiple
              accept=".png,.jpg,.jpeg,.webp,.zip"
              className="max-w-md cursor-pointer"
              onChange={(e) => setPreviewFiles(Array.from(e.target.files ?? []))}
            />
            <Button
              variant="outline"
              onClick={handleUploadPreviews}
              disabled={uploadPreviews.isPending || previewFiles.length === 0}
            >
              {uploadPreviews.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ImageIcon className="h-4 w-4" />
              )}
              {uploadPreviews.isPending ? "Caricamento…" : "Carica anteprime"}
            </Button>
          </div>
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
            <Card key={template.id} className="flex flex-col overflow-hidden">
              {template.preview_url && (
                <div className="aspect-[4/3] w-full overflow-hidden border-b border-border bg-muted">
                  <img
                    src={template.preview_url}
                    alt={`Anteprima ${template.name}`}
                    loading="lazy"
                    className="h-full w-full object-cover object-top"
                  />
                </div>
              )}
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
                {template.canva_url && (
                  <div className="mt-auto pt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full"
                      asChild
                    >
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
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
