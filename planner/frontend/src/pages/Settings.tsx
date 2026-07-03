import { useState } from "react";
import {
  CheckCircle2,
  FlaskConical,
  Save,
  XCircle,
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
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  useNotionSettings,
  useSaveNotionSettings,
  useSystemStatus,
} from "@/lib/queries";
import { formatDate } from "@/lib/utils";

function StatusRow({
  label,
  ok,
  okLabel = "Configurato",
  koLabel = "Non configurato",
}: {
  label: string;
  ok: boolean;
  okLabel?: string;
  koLabel?: string;
}) {
  return (
    <div className="flex items-center justify-between rounded-md border border-border/60 px-3 py-2 text-sm">
      <span className="font-medium">{label}</span>
      <span
        className={
          ok
            ? "inline-flex items-center gap-1 text-emerald-700"
            : "inline-flex items-center gap-1 text-muted-foreground"
        }
      >
        {ok ? (
          <CheckCircle2 className="h-4 w-4" />
        ) : (
          <XCircle className="h-4 w-4" />
        )}
        {ok ? okLabel : koLabel}
      </span>
    </div>
  );
}

export function Settings() {
  const { data: settings, isLoading } = useNotionSettings();
  const { data: system, isLoading: systemLoading } = useSystemStatus();
  const saveSettings = useSaveNotionSettings();

  const [token, setToken] = useState("");
  const [templatesDbId, setTemplatesDbId] = useState<string | null>(null);
  const [calendarPageId, setCalendarPageId] = useState<string | null>(null);

  const effectiveDbId = templatesDbId ?? settings?.templates_db_id ?? "";
  const effectivePageId =
    calendarPageId ?? settings?.calendar_parent_page_id ?? "";

  function handleSave() {
    const payload: {
      token?: string;
      templates_db_id?: string;
      calendar_parent_page_id?: string;
    } = {};
    if (token.trim()) payload.token = token.trim();
    if (templatesDbId !== null) payload.templates_db_id = templatesDbId.trim();
    if (calendarPageId !== null)
      payload.calendar_parent_page_id = calendarPageId.trim();

    if (Object.keys(payload).length === 0) {
      toast.info("Nessuna modifica da salvare");
      return;
    }
    saveSettings.mutate(payload, {
      onSuccess: () => {
        toast.success("Impostazioni Notion salvate");
        setToken("");
        setTemplatesDbId(null);
        setCalendarPageId(null);
      },
      onError: (err) => toast.error(`Errore: ${err.message}`),
    });
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">Impostazioni</h1>
        <p className="text-sm text-muted-foreground">
          Configurazione a livello agenzia (valida per tutti i brand).
        </p>
      </div>

      {/* Notion */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Notion</CardTitle>
              <CardDescription>
                Token dell'integrazione, database template Canva e pagina padre
                per i calendari editoriali.
              </CardDescription>
            </div>
            {isLoading ? (
              <Skeleton className="h-6 w-24" />
            ) : settings?.configured ? (
              <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Configurato
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 rounded-full border border-border bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">
                <XCircle className="h-3.5 w-3.5" />
                Non configurato
              </span>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="notion-token">Token integrazione</Label>
            <Input
              id="notion-token"
              type="password"
              placeholder={
                settings?.token_preview
                  ? `Attuale: ${settings.token_preview} — inserisci per sostituire`
                  : "ntn_…"
              }
              value={token}
              onChange={(e) => setToken(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="templates-db">Database template (ID)</Label>
            <Input
              id="templates-db"
              value={effectiveDbId}
              onChange={(e) => setTemplatesDbId(e.target.value)}
              placeholder="ID del database Notion con i template Canva"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="calendar-page">
              Pagina padre calendari (ID)
            </Label>
            <Input
              id="calendar-page"
              value={effectivePageId}
              onChange={(e) => setCalendarPageId(e.target.value)}
              placeholder="ID della pagina Notion sotto cui pubblicare i piani"
            />
          </div>
          <div className="flex items-center justify-between pt-1">
            <p className="text-xs text-muted-foreground">
              Template sincronizzati:{" "}
              <span className="font-medium text-foreground">
                {settings?.templates_synced ?? 0}
              </span>
              {settings?.templates_last_sync_at
                ? ` · ultima sync ${formatDate(settings.templates_last_sync_at, "long")}`
                : " · mai sincronizzati"}
            </p>
            <Button onClick={handleSave} disabled={saveSettings.isPending}>
              <Save className="h-4 w-4" />
              {saveSettings.isPending ? "Salvataggio…" : "Salva"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Stato sistema */}
      <Card>
        <CardHeader>
          <CardTitle>Stato sistema</CardTitle>
          <CardDescription>
            {system ? `Versione ${system.version}` : "Stato del backend"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {systemLoading ? (
            <>
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-9 w-full" />
            </>
          ) : system ? (
            <>
              <StatusRow label="Backend" ok={system.ok} okLabel="Online" koLabel="Offline" />
              <StatusRow
                label="API Claude (Anthropic)"
                ok={system.anthropic_configured}
              />
              <StatusRow label="Notion" ok={system.notion_configured} />
              {system.mock_mode && (
                <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                  <FlaskConical className="mt-0.5 h-4 w-4 shrink-0" />
                  <div>
                    <Badge
                      variant="outline"
                      className="mb-1 border-amber-300 bg-amber-100 text-amber-800"
                    >
                      mock_mode attivo
                    </Badge>
                    <p>
                      API Claude non configurata: generazione demo. I piani
                      generati sono deterministici e servono solo a provare il
                      flusso end-to-end.
                    </p>
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-muted-foreground">
              Impossibile contattare il backend.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
