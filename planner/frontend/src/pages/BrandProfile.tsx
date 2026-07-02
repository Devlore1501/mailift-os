import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Save } from "lucide-react";
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
import { Skeleton } from "@/components/ui/skeleton";
import { useBrand, useUpdateBrand } from "@/lib/queries";
import type { Brand } from "@/types/api";

interface FormState {
  name: string;
  description: string;
  tone_of_voice: string;
  mission: string;
  positioning: string;
  emails_per_week: number;
  avatar_who: string;
  avatar_desires: string;
  avatar_objections: string;
  avatar_language: string;
  avatar_notes: string;
}

function toFormState(brand: Brand): FormState {
  return {
    name: brand.name ?? "",
    description: brand.description ?? "",
    tone_of_voice: brand.tone_of_voice ?? "",
    mission: brand.mission ?? "",
    positioning: brand.positioning ?? "",
    emails_per_week: brand.emails_per_week ?? 3,
    avatar_who: brand.avatar?.who ?? "",
    avatar_desires: (brand.avatar?.desires ?? []).join("\n"),
    avatar_objections: (brand.avatar?.objections ?? []).join("\n"),
    avatar_language: brand.avatar?.language ?? "",
    avatar_notes: brand.avatar?.notes ?? "",
  };
}

function splitLines(value: string): string[] {
  return value
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
}

export function BrandProfile() {
  const { brandId: brandIdParam } = useParams();
  const brandId = Number(brandIdParam);
  const { data: brand, isLoading } = useBrand(brandId);
  const updateBrand = useUpdateBrand(brandId);

  const [form, setForm] = useState<FormState | null>(null);

  useEffect(() => {
    if (brand && !form) setForm(toFormState(brand));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [brand]);

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((f) => (f ? { ...f, [key]: value } : f));
  }

  function handleSave() {
    if (!form) return;
    if (!form.name.trim()) {
      toast.error("Il nome del brand è obbligatorio");
      return;
    }
    updateBrand.mutate(
      {
        name: form.name.trim(),
        description: form.description,
        tone_of_voice: form.tone_of_voice,
        mission: form.mission,
        positioning: form.positioning,
        emails_per_week: Number(form.emails_per_week) || 3,
        avatar: {
          who: form.avatar_who,
          desires: splitLines(form.avatar_desires),
          objections: splitLines(form.avatar_objections),
          language: form.avatar_language,
          notes: form.avatar_notes,
        },
      },
      {
        onSuccess: () => toast.success("Profilo brand salvato"),
        onError: (err) => toast.error(`Errore: ${err.message}`),
      }
    );
  }

  if (isLoading || !form) {
    return (
      <div className="mx-auto max-w-3xl space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Profilo brand
          </h1>
          <p className="text-sm text-muted-foreground">
            Questi dati alimentano la generazione dei piani editoriali.
          </p>
        </div>
        <Button onClick={handleSave} disabled={updateBrand.isPending}>
          <Save className="h-4 w-4" />
          {updateBrand.isPending ? "Salvataggio…" : "Salva profilo"}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Identità</CardTitle>
          <CardDescription>
            Chi è il brand e come parla ai suoi clienti.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Nome *</Label>
            <Input
              id="name"
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">Descrizione</Label>
            <Textarea
              id="description"
              rows={3}
              value={form.description}
              onChange={(e) => set("description", e.target.value)}
              placeholder="Cosa vende il brand, a chi, come…"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="tone">Tone of voice</Label>
            <Textarea
              id="tone"
              rows={2}
              value={form.tone_of_voice}
              onChange={(e) => set("tone_of_voice", e.target.value)}
              placeholder="es. prima persona, confidenziale, da enologo"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="mission">Mission</Label>
            <Textarea
              id="mission"
              rows={2}
              value={form.mission}
              onChange={(e) => set("mission", e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="positioning">Positioning</Label>
            <Textarea
              id="positioning"
              rows={2}
              value={form.positioning}
              onChange={(e) => set("positioning", e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="epw">Email a settimana</Label>
            <Input
              id="epw"
              type="number"
              min={1}
              max={7}
              className="w-32"
              value={form.emails_per_week}
              onChange={(e) => set("emails_per_week", Number(e.target.value))}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Avatar / Buyer persona</CardTitle>
          <CardDescription>
            Il cliente tipo a cui scrivono le email.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="who">Chi è</Label>
            <Textarea
              id="who"
              rows={2}
              value={form.avatar_who}
              onChange={(e) => set("avatar_who", e.target.value)}
              placeholder="es. appassionato di vino 35-60, acquista online…"
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="desires">Desideri (uno per riga)</Label>
              <Textarea
                id="desires"
                rows={4}
                value={form.avatar_desires}
                onChange={(e) => set("avatar_desires", e.target.value)}
                placeholder={"bere meglio\nscoprire cantine"}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="objections">Obiezioni (una per riga)</Label>
              <Textarea
                id="objections"
                rows={4}
                value={form.avatar_objections}
                onChange={(e) => set("avatar_objections", e.target.value)}
                placeholder={"prezzo\nspedizione"}
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="language">Linguaggio</Label>
            <Input
              id="language"
              value={form.avatar_language}
              onChange={(e) => set("avatar_language", e.target.value)}
              placeholder="es. informale, evocativo"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="avatar-notes">Note</Label>
            <Textarea
              id="avatar-notes"
              rows={2}
              value={form.avatar_notes}
              onChange={(e) => set("avatar_notes", e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={updateBrand.isPending}>
          <Save className="h-4 w-4" />
          {updateBrand.isPending ? "Salvataggio…" : "Salva profilo"}
        </Button>
      </div>
    </div>
  );
}
