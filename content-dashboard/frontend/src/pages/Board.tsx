// Piano editoriale: board Kanban drag-and-drop (FR-M1-04) con gate qualità visibile.
import { Filter, Plus } from "lucide-react";
import { DragEvent, useCallback, useEffect, useState } from "react";

import ContentModal from "@/components/ContentModal";
import { ErrorBox, PillarBadge, ScoreBadge, Spinner, WinnerBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { useApp } from "@/state/AppContext";
import type { Content } from "@/types";

export default function Board() {
  const { config, isEditor } = useApp();
  const [contents, setContents] = useState<Content[] | null>(null);
  const [error, setError] = useState("");
  const [gateMsg, setGateMsg] = useState("");
  const [openId, setOpenId] = useState<number | null>(null);
  const [dragOver, setDragOver] = useState<string | null>(null);
  const [filters, setFilters] = useState({ pillar: "", format: "", surface: "" });

  const gate = Number(config?.settings.critic_gate_min ?? 38);

  const load = useCallback(async () => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => v && params.set(k, v));
    setContents(await api.get<Content[]>(`/api/contents?${params}`));
  }, [filters]);

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, [load]);

  const statuses = (config?.statuses ?? []).filter((s) => s !== "archived");

  const onDrop = async (e: DragEvent, status: string) => {
    e.preventDefault();
    setDragOver(null);
    const id = Number(e.dataTransfer.getData("text/plain"));
    if (!id) return;
    setGateMsg("");
    try {
      await api.post(`/api/contents/${id}/status`, { status });
      await load();
    } catch (err) {
      setGateMsg((err as Error).message);
    }
  };

  const quickCreate = async () => {
    const created = await api.post<Content>("/api/contents", { surface: "reel" });
    await load();
    setOpenId(created.id);
  };

  if (error) return <ErrorBox message={error} />;
  if (!contents) return <Spinner />;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight">Piano editoriale</h1>
          <p className="text-sm text-ink-500">
            Gate qualità: score Critico ≥ {gate}/50 per programmare
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="w-4 h-4 text-ink-500" aria-hidden />
          <select className="input !w-auto" value={filters.pillar} aria-label="Filtra per pillar"
            onChange={(e) => setFilters({ ...filters, pillar: e.target.value })}>
            <option value="">Tutti i pillar</option>
            {Object.entries(config?.pillars ?? {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <select className="input !w-auto" value={filters.format} aria-label="Filtra per format"
            onChange={(e) => setFilters({ ...filters, format: e.target.value })}>
            <option value="">Tutti i format</option>
            {Object.entries(config?.formats ?? {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <select className="input !w-auto" value={filters.surface} aria-label="Filtra per surface"
            onChange={(e) => setFilters({ ...filters, surface: e.target.value })}>
            <option value="">Tutte le surface</option>
            {Object.entries(config?.surfaces ?? {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          {isEditor && (
            <button className="btn-gold" onClick={quickCreate}>
              <Plus className="w-4 h-4" aria-hidden /> Contenuto
            </button>
          )}
        </div>
      </div>

      {gateMsg && <ErrorBox message={gateMsg} />}

      <div className="grid gap-3 overflow-x-auto" style={{ gridTemplateColumns: `repeat(${statuses.length}, minmax(230px, 1fr))` }}>
        {statuses.map((status) => {
          const column = contents.filter((c) => c.status === status);
          return (
            <div
              key={status}
              onDragOver={(e) => { e.preventDefault(); setDragOver(status); }}
              onDragLeave={() => setDragOver((d) => (d === status ? null : d))}
              onDrop={(e) => onDrop(e, status)}
              className={`rounded-xl border p-2 min-h-[60vh] transition-colors duration-200 ${
                dragOver === status ? "border-gold-500 bg-gold-500/5" : "border-navy-700 bg-navy-900/60"
              }`}
            >
              <div className="flex items-center justify-between px-2 py-1.5 mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-ink-300">
                  {config?.status_labels[status]}
                </span>
                <span className="font-mono text-xs text-ink-500">{column.length}</span>
              </div>
              <div className="space-y-2">
                {column.map((c) => (
                  <button
                    key={c.id}
                    draggable
                    onDragStart={(e) => e.dataTransfer.setData("text/plain", String(c.id))}
                    onClick={() => setOpenId(c.id)}
                    className="card w-full text-left p-3 cursor-pointer hover:border-gold-500/50 transition-colors duration-200 block"
                  >
                    <div className="text-sm font-semibold leading-snug">
                      {c.title || c.idea_title || `Contenuto #${c.id}`}
                    </div>
                    <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                      <PillarBadge pillar={c.pillar} label={config?.pillars[c.pillar ?? ""]} />
                      <span className="text-[11px] text-ink-500">
                        {config?.surfaces[c.surface]}
                        {c.format ? ` · ${config?.formats[c.format]}` : ""}
                      </span>
                    </div>
                    <div className="flex items-center justify-between mt-2">
                      <ScoreBadge score={c.critic_score} gate={gate} />
                      <div className="flex items-center gap-1.5">
                        {c.is_winner && <WinnerBadge />}
                        {(c.scheduled_at || c.published_at) && (
                          <span className="font-mono text-[11px] text-ink-500">
                            {fmtDate(c.published_at ?? c.scheduled_at)}
                          </span>
                        )}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {openId !== null && (
        <ContentModal contentId={openId} onClose={() => setOpenId(null)} onChanged={() => load()} />
      )}
    </div>
  );
}
