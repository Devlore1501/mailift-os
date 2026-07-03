import { useState } from "react";
import {
  ChevronDown,
  Clock,
  ExternalLink,
  Loader2,
  Package,
  Pencil,
  RefreshCw,
  Tag,
  Users,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
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
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ObjectiveBadge } from "@/components/domain/ObjectiveBadge";
import { useRegenerateEmail, useUpdatePlanEmail } from "@/lib/queries";
import { cn, formatDate } from "@/lib/utils";
import type { PlanEmail } from "@/types/api";

interface EmailCardProps {
  email: PlanEmail;
  planId: number;
  readOnly?: boolean;
}

export function EmailCard({ email, planId, readOnly = false }: EmailCardProps) {
  const [bodyOpen, setBodyOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [regenOpen, setRegenOpen] = useState(false);

  // Stato form modifica
  const [sendTime, setSendTime] = useState(email.send_time);
  const [subjects, setSubjects] = useState(email.subject_variants.join("\n"));
  const [previewText, setPreviewText] = useState(email.preview_text);
  const [body, setBody] = useState(email.body);
  const [instructions, setInstructions] = useState("");

  const updateEmail = useUpdatePlanEmail(planId);
  const regenerate = useRegenerateEmail(planId);

  const isRegenerating =
    regenerate.isPending && regenerate.variables?.emailId === email.id;

  function openEdit() {
    setSendTime(email.send_time);
    setSubjects(email.subject_variants.join("\n"));
    setPreviewText(email.preview_text);
    setBody(email.body);
    setEditOpen(true);
  }

  function handleSave() {
    const variants = subjects
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
    if (variants.length === 0) {
      toast.error("Inserisci almeno un oggetto");
      return;
    }
    updateEmail.mutate(
      {
        emailId: email.id,
        data: {
          send_time: sendTime,
          subject_variants: variants,
          preview_text: previewText,
          body,
        },
      },
      {
        onSuccess: () => {
          toast.success("Email aggiornata");
          setEditOpen(false);
        },
        onError: (err) => toast.error(`Errore: ${err.message}`),
      }
    );
  }

  function handleRegenerate() {
    setRegenOpen(false);
    regenerate.mutate(
      {
        emailId: email.id,
        instructions: instructions.trim() || undefined,
      },
      {
        onSuccess: () => {
          toast.success(`Email #${email.position} rigenerata`);
          setInstructions("");
        },
        onError: (err) => toast.error(`Errore rigenerazione: ${err.message}`),
      }
    );
  }

  return (
    <Card className={cn("relative", isRegenerating && "opacity-80")}>
      {isRegenerating && (
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 rounded-lg bg-background/70 backdrop-blur-[2px]">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <span className="text-sm font-medium text-muted-foreground">
            Rigenerazione in corso… può richiedere fino a 40 secondi
          </span>
        </div>
      )}

      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-3">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-muted text-sm font-semibold">
              {email.position}
            </span>
            <div className="leading-tight">
              <div className="text-sm font-semibold capitalize">
                {email.send_day} {formatDate(email.send_date)}
              </div>
              <div className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
                {email.send_time}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {email.status === "edited" && (
              <Badge variant="outline" className="text-[11px]">
                Modificata
              </Badge>
            )}
            <ObjectiveBadge objective={email.objective} />
            {!readOnly && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={openEdit}
                  disabled={isRegenerating}
                >
                  <Pencil className="h-3.5 w-3.5" />
                  Modifica
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setRegenOpen(true)}
                  disabled={isRegenerating}
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Rigenera
                </Button>
              </>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Tema + angolo */}
        <div>
          <div className="text-sm font-semibold">{email.theme}</div>
          {email.angle && (
            <div className="text-sm text-muted-foreground">{email.angle}</div>
          )}
        </div>

        {/* Segmento */}
        {email.segment && (
          <div className="flex items-start gap-2 rounded-md border border-border/60 bg-muted/40 px-3 py-2">
            <Users className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
            <div className="min-w-0 text-sm">
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="cursor-help font-medium underline decoration-dotted underline-offset-2">
                    {email.segment.name}
                  </span>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  {email.segment.rationale || "Nessuna motivazione"}
                </TooltipContent>
              </Tooltip>
              {email.segment.rationale && (
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {email.segment.rationale}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Oggetti A/B + preview */}
        <div className="space-y-1.5">
          <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Oggetti A/B
          </div>
          <ul className="space-y-1">
            {email.subject_variants.map((subject, i) => (
              <li key={i} className="flex items-center gap-2 text-sm">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-muted text-[11px] font-semibold text-muted-foreground">
                  {String.fromCharCode(65 + i)}
                </span>
                <span>{subject}</span>
              </li>
            ))}
          </ul>
          {email.preview_text && (
            <p className="pt-1 text-xs text-muted-foreground">
              <span className="font-medium">Preview:</span> {email.preview_text}
            </p>
          )}
        </div>

        {/* Corpo espandibile */}
        <div className="rounded-md border border-border/60">
          <button
            type="button"
            className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium hover:bg-muted/50"
            onClick={() => setBodyOpen((o) => !o)}
            aria-expanded={bodyOpen}
          >
            Corpo email
            <ChevronDown
              className={cn(
                "h-4 w-4 text-muted-foreground transition-transform",
                bodyOpen && "rotate-180"
              )}
            />
          </button>
          {bodyOpen && (
            <div className="border-t border-border/60 px-3 py-3">
              <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-foreground">
                {email.body}
              </pre>
            </div>
          )}
        </div>

        {/* Prodotti + offerta */}
        {(email.products.length > 0 || email.offer) && (
          <div className="flex flex-wrap items-center gap-2">
            {email.products.map((p, i) => (
              <Tooltip key={i}>
                <TooltipTrigger asChild>
                  <span className="inline-flex cursor-help items-center gap-1 rounded-full border border-border bg-muted/60 px-2 py-0.5 text-xs font-medium">
                    <Package className="h-3 w-3" />
                    {p.name}
                  </span>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  {p.reason || p.name}
                </TooltipContent>
              </Tooltip>
            ))}
            {email.offer && (
              <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
                <Tag className="h-3 w-3" />
                {email.offer.name}
                {email.offer.code ? ` · ${email.offer.code}` : ""}
                {email.offer.discount ? ` (${email.offer.discount})` : ""}
              </span>
            )}
          </div>
        )}

        {/* Template Canva */}
        {email.canva_template && (
          <div className="flex items-center justify-between gap-3 rounded-md border border-border/60 px-3 py-2">
            <div className="flex min-w-0 items-center gap-3">
              {email.canva_template.preview_url && (
                <img
                  src={email.canva_template.preview_url}
                  alt={`Anteprima ${email.canva_template.name}`}
                  loading="lazy"
                  className="h-14 w-11 shrink-0 rounded border border-border object-cover object-top"
                />
              )}
              <div className="min-w-0 text-sm">
                <span className="font-medium">{email.canva_template.name}</span>
                <span className="ml-2 rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">
                  {email.canva_template.category}
                </span>
              </div>
            </div>
            {email.canva_template.canva_url && (
              <Button variant="outline" size="sm" asChild>
                <a
                  href={email.canva_template.canva_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  Apri in Canva
                </a>
              </Button>
            )}
          </div>
        )}
      </CardContent>

      {/* Dialog modifica */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Modifica email #{email.position}</DialogTitle>
            <DialogDescription>
              Le modifiche manuali marcano l'email come "modificata".
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor={`send-time-${email.id}`}>Orario di invio</Label>
              <Input
                id={`send-time-${email.id}`}
                type="time"
                className="w-40"
                value={sendTime}
                onChange={(e) => setSendTime(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor={`subjects-${email.id}`}>
                Oggetti A/B (uno per riga)
              </Label>
              <Textarea
                id={`subjects-${email.id}`}
                rows={3}
                value={subjects}
                onChange={(e) => setSubjects(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor={`preview-${email.id}`}>Preview text</Label>
              <Input
                id={`preview-${email.id}`}
                value={previewText}
                onChange={(e) => setPreviewText(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor={`body-${email.id}`}>Corpo email</Label>
              <Textarea
                id={`body-${email.id}`}
                rows={12}
                className="font-mono text-xs"
                value={body}
                onChange={(e) => setBody(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditOpen(false)}>
              Annulla
            </Button>
            <Button onClick={handleSave} disabled={updateEmail.isPending}>
              {updateEmail.isPending ? "Salvataggio…" : "Salva modifiche"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog rigenera */}
      <Dialog open={regenOpen} onOpenChange={setRegenOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rigenera email #{email.position}</DialogTitle>
            <DialogDescription>
              Claude rigenera l'email da zero. L'operazione può richiedere fino
              a 40 secondi.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2 py-2">
            <Label htmlFor={`instructions-${email.id}`}>
              Istruzioni (opzionali)
            </Label>
            <Textarea
              id={`instructions-${email.id}`}
              rows={3}
              placeholder="es. più corta, più urgenza, cita il best seller…"
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRegenOpen(false)}>
              Annulla
            </Button>
            <Button onClick={handleRegenerate}>
              <RefreshCw className="h-3.5 w-3.5" />
              Rigenera
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
