// Mailift Email Planner — calendario invii + pipeline campagne per cliente.
import {
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  KanbanSquare,
  Loader2,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import { DragEvent, useCallback, useEffect, useMemo, useState } from "react";

// ---- API ----

class ApiError extends Error {}

async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    ...options,
    headers: options.body ? { "Content-Type": "application/json" } : undefined,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch { /* non JSON */ }
    throw new ApiError(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

// ---- Tipi ----

interface Config {
  statuses: string[];
  status_labels: Record<string, string>;
  types: Record<string, string>;
}

interface Client {
  id: number;
  name: string;
  active: boolean;
  program_notes: string | null;
  tone_notes: string | null;
}

interface Campaign {
  id: number;
  client_id: number;
  client_name: string | null;
  title: string;
  type: string;
  status: string;
  subject: string | null;
  preview_text: string | null;
  brief: string | null;
  scheduled_at: string | null;
  sent_at: string | null;
  klaviyo_url: string | null;
  open_rate_pct: number | null;
  ctr_pct: number | null;
  revenue: number | null;
}

// ---- Utility ----

const CLIENT_COLORS = ["#E0A93B", "#5B9DD9", "#3DCB8F", "#B287E8", "#E5734B", "#6AC7C7"];
const clientColor = (id: number) => CLIENT_COLORS[id % CLIENT_COLORS.length];

function toDateKey(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function startOfWeek(d: Date): Date {
  const out = new Date(d);
  out.setDate(d.getDate() - ((d.getDay() + 6) % 7));
  out.setHours(0, 0, 0, 0);
  return out;
}

const fmtTime = (iso: string) =>
  new Date(iso).toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" });

// ---- App ----

export default function App() {
  const [config, setConfig] = useState<Config | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[] | null>(null);
  const [view, setView] = useState<"calendar" | "board">("calendar");
  const [clientFilter, setClientFilter] = useState<number | null>(null);
  const [anchor, setAnchor] = useState(() => new Date());
  const [openCampaign, setOpenCampaign] = useState<Campaign | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const params = clientFilter ? `?client_id=${clientFilter}` : "";
    setCampaigns(await api<Campaign[]>(`/api/campaigns${params}`));
  }, [clientFilter]);

  useEffect(() => {
    Promise.all([api<Config>("/api/config"), api<Client[]>("/api/clients")])
      .then(([cfg, cls]) => {
        setConfig(cfg);
        setClients(cls);
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, [load]);

  if (error && !campaigns) {
    return <div className="p-8 text-warn">{error}</div>;
  }
  if (!config || !campaigns) {
    return (
      <div className="min-h-screen flex items-center justify-center text-ink-500 gap-2">
        <Loader2 className="w-4 h-4 animate-spin" aria-hidden /> Caricamento…
      </div>
    );
  }

  return (
    <div className="min-h-screen p-6 lg:p-8 max-w-[1500px] mx-auto space-y-5">
      <header className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="font-extrabold text-2xl tracking-tight">
            Mailift<span className="text-gold-500">.</span> Email Planner
          </div>
          <p className="text-sm text-ink-500">Piano invii dei clienti retainer</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex gap-1" role="group" aria-label="Vista">
            {([["calendar", "Calendario", CalendarDays], ["board", "Pipeline", KanbanSquare]] as const).map(
              ([key, label, Icon]) => (
                <button
                  key={key}
                  onClick={() => setView(key)}
                  className={`btn text-xs border ${
                    view === key
                      ? "bg-gold-500 text-navy-950 border-gold-500"
                      : "bg-navy-800 text-ink-300 border-navy-700 hover:border-gold-500/50"
                  }`}
                >
                  <Icon className="w-4 h-4" aria-hidden /> {label}
                </button>
              ),
            )}
          </div>
          <button className="btn-gold" onClick={() => setCreating(true)}>
            <Plus className="w-4 h-4" aria-hidden /> Campagna
          </button>
        </div>
      </header>

      {/* filtro clienti */}
      <div className="flex gap-1.5 flex-wrap" role="group" aria-label="Filtra per cliente">
        <button
          onClick={() => setClientFilter(null)}
          className={`rounded-md px-3 py-1.5 text-xs font-semibold border transition-colors duration-200 cursor-pointer ${
            clientFilter === null
              ? "bg-gold-500 text-navy-950 border-gold-500"
              : "bg-navy-800 text-ink-300 border-navy-700 hover:border-gold-500/50"
          }`}
        >
          Tutti i clienti
        </button>
        {clients.map((c) => (
          <button
            key={c.id}
            onClick={() => setClientFilter(clientFilter === c.id ? null : c.id)}
            title={c.program_notes ?? undefined}
            className={`rounded-md px-3 py-1.5 text-xs font-semibold border transition-colors duration-200 cursor-pointer inline-flex items-center gap-1.5 ${
              clientFilter === c.id
                ? "bg-gold-500 text-navy-950 border-gold-500"
                : "bg-navy-800 text-ink-300 border-navy-700 hover:border-gold-500/50"
            }`}
          >
            <span className="w-2 h-2 rounded-full" style={{ background: clientColor(c.id) }} aria-hidden />
            {c.name}
          </button>
        ))}
      </div>

      {error && <div className="rounded-lg border border-warn/40 bg-warn/10 text-warn px-3 py-2 text-sm">{error}</div>}

      {view === "calendar" ? (
        <CalendarView
          campaigns={campaigns}
          anchor={anchor}
          setAnchor={setAnchor}
          onOpen={setOpenCampaign}
        />
      ) : (
        <BoardView
          campaigns={campaigns}
          config={config}
          onOpen={setOpenCampaign}
          onError={setError}
          reload={load}
        />
      )}

      {(openCampaign || creating) && (
        <CampaignModal
          campaign={openCampaign}
          clients={clients}
          config={config}
          onClose={() => {
            setOpenCampaign(null);
            setCreating(false);
          }}
          onChanged={() => load().catch((e) => setError(e.message))}
        />
      )}
    </div>
  );
}

// ---- Calendario ----

function CalendarView({
  campaigns,
  anchor,
  setAnchor,
  onOpen,
}: {
  campaigns: Campaign[];
  anchor: Date;
  setAnchor: (d: Date) => void;
  onOpen: (c: Campaign) => void;
}) {
  const days = useMemo(() => {
    const first = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
    const start = startOfWeek(first);
    return Array.from({ length: 42 }, (_, i) => new Date(start.getTime() + i * 86400_000));
  }, [anchor]);

  const byDay = useMemo(() => {
    const map = new Map<string, Campaign[]>();
    for (const c of campaigns) {
      const iso = c.scheduled_at ?? c.sent_at;
      if (!iso) continue;
      const key = toDateKey(new Date(iso));
      map.set(key, [...(map.get(key) ?? []), c]);
    }
    return map;
  }, [campaigns]);

  const todayKey = toDateKey(new Date());
  const monthLabel = anchor.toLocaleDateString("it-IT", { month: "long", year: "numeric" });
  const unscheduled = campaigns.filter((c) => !c.scheduled_at && !c.sent_at);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-end gap-2">
        <button className="btn-ghost !p-2" aria-label="Mese precedente"
          onClick={() => setAnchor(new Date(anchor.getFullYear(), anchor.getMonth() - 1, 1))}>
          <ChevronLeft className="w-4 h-4" aria-hidden />
        </button>
        <span className="text-sm font-semibold capitalize min-w-36 text-center">{monthLabel}</span>
        <button className="btn-ghost !p-2" aria-label="Mese successivo"
          onClick={() => setAnchor(new Date(anchor.getFullYear(), anchor.getMonth() + 1, 1))}>
          <ChevronRight className="w-4 h-4" aria-hidden />
        </button>
      </div>
      <div className="card overflow-hidden">
        <div className="grid grid-cols-7 border-b border-navy-700">
          {["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"].map((d) => (
            <div key={d} className="px-2 py-2 text-xs font-bold uppercase tracking-wider text-ink-500 text-center">{d}</div>
          ))}
        </div>
        <div className="grid grid-cols-7">
          {days.map((day) => {
            const key = toDateKey(day);
            const items = byDay.get(key) ?? [];
            const inMonth = day.getMonth() === anchor.getMonth();
            return (
              <div key={key} className={`border-b border-r border-navy-700/50 p-1.5 min-h-[104px] ${inMonth ? "" : "opacity-40"}`}>
                <div className={`text-xs font-mono mb-1 px-1 ${key === todayKey ? "text-gold-400 font-bold" : "text-ink-500"}`}>
                  {day.getDate()}
                </div>
                <div className="space-y-1">
                  {items.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => onOpen(c)}
                      className={`w-full text-left rounded-md px-1.5 py-1 text-[11px] leading-tight font-medium cursor-pointer border transition-colors duration-200 ${
                        c.status === "inviata"
                          ? "bg-navy-700/50 border-navy-600 text-ink-300 hover:border-gold-500/50"
                          : "bg-gold-500/10 border-gold-500/30 text-gold-400 hover:border-gold-500"
                      }`}
                      title={`${c.client_name} — ${c.title}`}
                    >
                      <span className="inline-block w-1.5 h-1.5 rounded-full mr-1"
                        style={{ background: clientColor(c.client_id) }} aria-hidden />
                      {c.scheduled_at && <span className="font-mono">{fmtTime(c.scheduled_at)}</span>} {c.title.slice(0, 28)}
                      <span className="text-ink-500 block pl-3">{c.client_name}</span>
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
      {unscheduled.length > 0 && (
        <p className="text-xs text-ink-500">
          {unscheduled.length} campagn{unscheduled.length === 1 ? "a" : "e"} senza data — le trovi nella Pipeline.
        </p>
      )}
    </div>
  );
}

// ---- Pipeline ----

function BoardView({
  campaigns,
  config,
  onOpen,
  onError,
  reload,
}: {
  campaigns: Campaign[];
  config: Config;
  onOpen: (c: Campaign) => void;
  onError: (msg: string) => void;
  reload: () => Promise<void>;
}) {
  const [dragOver, setDragOver] = useState<string | null>(null);

  const onDrop = async (e: DragEvent, status: string) => {
    e.preventDefault();
    setDragOver(null);
    const id = Number(e.dataTransfer.getData("text/plain"));
    if (!id) return;
    onError("");
    try {
      await api(`/api/campaigns/${id}/status`, { method: "POST", body: JSON.stringify({ status }) });
      await reload();
    } catch (err) {
      onError((err as Error).message);
    }
  };

  return (
    <div className="grid gap-3 overflow-x-auto" style={{ gridTemplateColumns: `repeat(${config.statuses.length}, minmax(220px, 1fr))` }}>
      {config.statuses.map((status) => {
        const column = campaigns.filter((c) => c.status === status);
        return (
          <div
            key={status}
            onDragOver={(e) => { e.preventDefault(); setDragOver(status); }}
            onDragLeave={() => setDragOver((d) => (d === status ? null : d))}
            onDrop={(e) => onDrop(e, status)}
            className={`rounded-xl border p-2 min-h-[55vh] transition-colors duration-200 ${
              dragOver === status ? "border-gold-500 bg-gold-500/5" : "border-navy-700 bg-navy-900/60"
            }`}
          >
            <div className="flex items-center justify-between px-2 py-1.5 mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-ink-300">
                {config.status_labels[status]}
              </span>
              <span className="font-mono text-xs text-ink-500">{column.length}</span>
            </div>
            <div className="space-y-2">
              {column.map((c) => (
                <button
                  key={c.id}
                  draggable
                  onDragStart={(e) => e.dataTransfer.setData("text/plain", String(c.id))}
                  onClick={() => onOpen(c)}
                  className="card w-full text-left p-3 cursor-pointer hover:border-gold-500/50 transition-colors duration-200 block"
                >
                  <div className="text-sm font-semibold leading-snug">{c.title}</div>
                  <div className="flex items-center gap-1.5 mt-2 text-[11px] text-ink-500">
                    <span className="w-2 h-2 rounded-full shrink-0" style={{ background: clientColor(c.client_id) }} aria-hidden />
                    {c.client_name} · {config.types[c.type]}
                  </div>
                  <div className="flex items-center justify-between mt-1.5">
                    {c.scheduled_at ? (
                      <span className="font-mono text-[11px] text-ink-300">
                        {new Date(c.scheduled_at).toLocaleDateString("it-IT", { day: "2-digit", month: "short" })} {fmtTime(c.scheduled_at)}
                      </span>
                    ) : (
                      <span className="text-[11px] text-warn">senza data</span>
                    )}
                    {c.status === "inviata" && c.open_rate_pct !== null && (
                      <span className="font-mono text-[11px] text-ok">{c.open_rate_pct}% open</span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ---- Modal campagna ----

function CampaignModal({
  campaign,
  clients,
  config,
  onClose,
  onChanged,
}: {
  campaign: Campaign | null;
  clients: Client[];
  config: Config;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [draft, setDraft] = useState(() => ({
    client_id: campaign?.client_id ?? clients[0]?.id ?? 0,
    title: campaign?.title ?? "",
    type: campaign?.type ?? "campagna",
    subject: campaign?.subject ?? "",
    preview_text: campaign?.preview_text ?? "",
    brief: campaign?.brief ?? "",
    scheduled_at: campaign?.scheduled_at ? campaign.scheduled_at.slice(0, 16) : "",
    klaviyo_url: campaign?.klaviyo_url ?? "",
    open_rate_pct: campaign?.open_rate_pct?.toString() ?? "",
    ctr_pct: campaign?.ctr_pct?.toString() ?? "",
    revenue: campaign?.revenue?.toString() ?? "",
  }));
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const client = clients.find((c) => c.id === Number(draft.client_id));

  const save = async () => {
    if (!draft.title.trim()) {
      setError("Il titolo è obbligatorio");
      return;
    }
    setSaving(true);
    setError("");
    const body = {
      client_id: Number(draft.client_id),
      title: draft.title,
      type: draft.type,
      subject: draft.subject || null,
      preview_text: draft.preview_text || null,
      brief: draft.brief || null,
      scheduled_at: draft.scheduled_at ? new Date(draft.scheduled_at).toISOString() : null,
      klaviyo_url: draft.klaviyo_url || null,
      open_rate_pct: draft.open_rate_pct === "" ? null : Number(draft.open_rate_pct),
      ctr_pct: draft.ctr_pct === "" ? null : Number(draft.ctr_pct),
      revenue: draft.revenue === "" ? null : Number(draft.revenue),
    };
    try {
      if (campaign) {
        await api(`/api/campaigns/${campaign.id}`, { method: "PATCH", body: JSON.stringify(body) });
      } else {
        await api("/api/campaigns", { method: "POST", body: JSON.stringify(body) });
      }
      onChanged();
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const changeStatus = async (status: string) => {
    if (!campaign) return;
    setError("");
    try {
      await api(`/api/campaigns/${campaign.id}/status`, { method: "POST", body: JSON.stringify({ status }) });
      onChanged();
      onClose();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const remove = async () => {
    if (!campaign || !window.confirm(`Eliminare "${campaign.title}"?`)) return;
    await api(`/api/campaigns/${campaign.id}`, { method: "DELETE" });
    onChanged();
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-navy-950/80 backdrop-blur-sm p-4 overflow-y-auto"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
      role="dialog"
      aria-modal="true"
    >
      <div className="card w-full max-w-2xl mt-8 mb-8">
        <div className="flex items-center justify-between px-5 py-4 border-b border-navy-700">
          <h2 className="font-bold text-lg">{campaign ? campaign.title : "Nuova campagna"}</h2>
          <button className="btn-ghost !p-2" onClick={onClose} aria-label="Chiudi">
            <X className="w-4 h-4" aria-hidden />
          </button>
        </div>
        <div className="p-5 space-y-4">
          {campaign && (
            <div className="flex flex-wrap gap-1.5" role="group" aria-label="Stato">
              {config.statuses.map((s) => (
                <button
                  key={s}
                  onClick={() => s !== campaign.status && changeStatus(s)}
                  className={`rounded-md px-2.5 py-1 text-xs font-semibold transition-colors duration-200 cursor-pointer border ${
                    s === campaign.status
                      ? "bg-gold-500 text-navy-950 border-gold-500"
                      : "bg-navy-900 text-ink-300 border-navy-700 hover:border-gold-500/50"
                  }`}
                >
                  {config.status_labels[s]}
                </button>
              ))}
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-warn/40 bg-warn/10 text-warn px-3 py-2 text-sm" role="alert">{error}</div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="label" htmlFor="c-client">Cliente</label>
              <select id="c-client" className="input" value={draft.client_id}
                onChange={(e) => setDraft({ ...draft, client_id: Number(e.target.value) })}>
                {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              {client?.program_notes && (
                <p className="text-[11px] text-ink-500 mt-1">{client.program_notes}</p>
              )}
            </div>
            <div>
              <label className="label" htmlFor="c-type">Tipo</label>
              <select id="c-type" className="input" value={draft.type}
                onChange={(e) => setDraft({ ...draft, type: e.target.value })}>
                {Object.entries(config.types).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="label" htmlFor="c-title">Titolo (interno) *</label>
              <input id="c-title" className="input" value={draft.title}
                onChange={(e) => setDraft({ ...draft, title: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="c-subject">Oggetto email</label>
              <input id="c-subject" className="input" value={draft.subject}
                onChange={(e) => setDraft({ ...draft, subject: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="c-preview">Preview text</label>
              <input id="c-preview" className="input" value={draft.preview_text}
                onChange={(e) => setDraft({ ...draft, preview_text: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="c-sched">Data e ora invio</label>
              <input id="c-sched" className="input font-mono" type="datetime-local" value={draft.scheduled_at}
                onChange={(e) => setDraft({ ...draft, scheduled_at: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="c-klaviyo">Link Klaviyo</label>
              <input id="c-klaviyo" className="input font-mono text-xs" value={draft.klaviyo_url}
                onChange={(e) => setDraft({ ...draft, klaviyo_url: e.target.value })} />
            </div>
            <div className="md:col-span-2">
              <label className="label" htmlFor="c-brief">Brief / note{client?.tone_notes ? ` · Tono: ${client.tone_notes}` : ""}</label>
              <textarea id="c-brief" className="input min-h-[100px]" value={draft.brief}
                onChange={(e) => setDraft({ ...draft, brief: e.target.value })} />
            </div>
          </div>

          {campaign?.status === "inviata" && (
            <div>
              <span className="label">Risultati (per il report settimanale)</span>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="label" htmlFor="c-open">Open rate %</label>
                  <input id="c-open" className="input font-mono" type="number" step="0.1" value={draft.open_rate_pct}
                    onChange={(e) => setDraft({ ...draft, open_rate_pct: e.target.value })} />
                </div>
                <div>
                  <label className="label" htmlFor="c-ctr">CTR %</label>
                  <input id="c-ctr" className="input font-mono" type="number" step="0.1" value={draft.ctr_pct}
                    onChange={(e) => setDraft({ ...draft, ctr_pct: e.target.value })} />
                </div>
                <div>
                  <label className="label" htmlFor="c-rev">Revenue €</label>
                  <input id="c-rev" className="input font-mono" type="number" step="1" value={draft.revenue}
                    onChange={(e) => setDraft({ ...draft, revenue: e.target.value })} />
                </div>
              </div>
            </div>
          )}

          <div className="flex justify-between items-center pt-1">
            {campaign ? (
              <button className="btn-danger" onClick={remove}>
                <Trash2 className="w-4 h-4" aria-hidden /> Elimina
              </button>
            ) : <span />}
            <button className="btn-gold" onClick={save} disabled={saving}>
              {saving ? "Salvataggio…" : "Salva"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
