// Dettaglio contenuto: brief/script, programmazione, score Critico, metriche.
import { ExternalLink, Plus, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import { fmtDateTime, num, pct, ratePct } from "@/lib/format";
import { useApp } from "@/state/AppContext";
import type { Content, Metric } from "@/types";
import { ErrorBox, Modal, PillarBadge, ScoreBadge, Spinner } from "./ui";

const METRIC_INPUTS: { key: keyof MetricDraft; label: string; step?: string }[] = [
  { key: "views", label: "Views" },
  { key: "likes", label: "Likes" },
  { key: "avg_retention_pct", label: "Retention media %", step: "0.1" },
  { key: "hook_retention_pct", label: "Hook retention %", step: "0.1" },
  { key: "rewatch_rate", label: "Rewatch rate (0-1)", step: "0.001" },
  { key: "saves", label: "Saves" },
  { key: "shares", label: "Shares" },
  { key: "comments", label: "Commenti" },
  { key: "icp_comments", label: "Commenti ICP" },
  { key: "non_icp_comments", label: "Commenti non-ICP" },
  { key: "dm_keyword_triggers", label: "DM keyword trigger" },
  { key: "fhs_clicks", label: "Click FHS" },
  { key: "fhs_purchases", label: "Acquisti FHS" },
];

type MetricDraft = Record<string, string>;

export default function ContentModal({
  contentId,
  onClose,
  onChanged,
}: {
  contentId: number;
  onClose: () => void;
  onChanged: () => void;
}) {
  const { config, user, isEditor } = useApp();
  const [content, setContent] = useState<Content | null>(null);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [tab, setTab] = useState<"brief" | "metrics">("brief");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [metricDraft, setMetricDraft] = useState<MetricDraft>({});

  const gate = Number(config?.settings.critic_gate_min ?? 38);
  const contributorLocked = user?.role === "contributor";

  const load = useCallback(async () => {
    const c = await api.get<Content>(`/api/contents/${contentId}`);
    setContent(c);
    setDraft({
      title: c.title ?? "",
      script: c.script ?? "",
      hook: c.hook ?? "",
      cta_keyword: c.cta_keyword ?? "",
      notes: c.notes ?? "",
      external_url: c.external_url ?? "",
      asset_links: c.asset_links.join("\n"),
      critic_score: c.critic_score?.toString() ?? "",
      scheduled_at: c.scheduled_at ? c.scheduled_at.slice(0, 16) : "",
      format: c.format ?? "",
      surface: c.surface,
      pillar: c.pillar ?? "",
      platform: c.platform ?? "instagram",
    });
    setMetrics(await api.get<Metric[]>(`/api/contents/${contentId}/metrics`));
  }, [contentId]);

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, [load]);

  const save = async () => {
    if (!content) return;
    setSaving(true);
    setError("");
    try {
      const body: Record<string, unknown> = {
        title: draft.title || null,
        script: draft.script || null,
        hook: draft.hook || null,
        cta_keyword: draft.cta_keyword || null,
        notes: draft.notes || null,
        asset_links: draft.asset_links.split("\n").map((s) => s.trim()).filter(Boolean),
      };
      if (!contributorLocked) {
        body.external_url = draft.external_url || null;
        body.critic_score = draft.critic_score === "" ? null : Number(draft.critic_score);
        body.scheduled_at = draft.scheduled_at ? new Date(draft.scheduled_at).toISOString() : null;
        body.format = draft.format || null;
        body.surface = draft.surface;
        body.pillar = draft.pillar || null;
        body.platform = draft.platform || null;
      }
      await api.patch(`/api/contents/${content.id}`, body);
      await load();
      onChanged();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const changeStatus = async (status: string) => {
    if (!content) return;
    setError("");
    try {
      await api.post(`/api/contents/${content.id}/status`, { status });
      await load();
      onChanged();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const addMetric = async () => {
    if (!content) return;
    setError("");
    const body: Record<string, number> = {};
    for (const [key, value] of Object.entries(metricDraft)) {
      if (value !== "") body[key] = Number(value);
    }
    if (Object.keys(body).length === 0) {
      setError("Inserisci almeno un valore");
      return;
    }
    try {
      await api.post(`/api/contents/${content.id}/metrics`, body);
      setMetricDraft({});
      await load();
      onChanged();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  if (!content) {
    return (
      <Modal title="Contenuto" onClose={onClose} wide>
        {error ? <ErrorBox message={error} /> : <Spinner />}
      </Modal>
    );
  }

  const statuses = config?.statuses ?? [];
  const labels = config?.status_labels ?? {};

  return (
    <Modal
      title={content.title || content.idea_title || `Contenuto #${content.id}`}
      onClose={onClose}
      wide
    >
      <div className="flex items-center gap-2 flex-wrap mb-4">
        <PillarBadge pillar={content.pillar} label={config?.pillars[content.pillar ?? ""]} />
        <span className="text-xs text-ink-500">{config?.surfaces[content.surface]}</span>
        {content.format && <span className="text-xs text-ink-500">· {config?.formats[content.format]}</span>}
        {content.idea_title && (
          <span className="text-xs text-ink-500">· Idea madre: “{content.idea_title}”</span>
        )}
        <ScoreBadge score={content.critic_score} gate={gate} />
      </div>

      {/* pipeline di stato */}
      <div className="flex flex-wrap gap-1.5 mb-4" role="group" aria-label="Stato pipeline">
        {statuses.map((s) => (
          <button
            key={s}
            onClick={() => s !== content.status && changeStatus(s)}
            className={`rounded-md px-2.5 py-1 text-xs font-semibold transition-colors duration-200 cursor-pointer border ${
              s === content.status
                ? "bg-gold-500 text-navy-950 border-gold-500"
                : "bg-navy-900 text-ink-300 border-navy-700 hover:border-gold-500/50"
            }`}
          >
            {labels[s] ?? s}
          </button>
        ))}
      </div>

      {error && <div className="mb-4"><ErrorBox message={error} /></div>}

      <div className="flex gap-1 border-b border-navy-700 mb-4" role="tablist">
        {(["brief", "metrics"] as const).map((t) => (
          <button
            key={t}
            role="tab"
            aria-selected={tab === t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-sm font-semibold transition-colors cursor-pointer border-b-2 -mb-px ${
              tab === t ? "border-gold-500 text-gold-400" : "border-transparent text-ink-500 hover:text-ink-300"
            }`}
          >
            {t === "brief" ? "Brief & script" : `Metriche (${metrics.length})`}
          </button>
        ))}
      </div>

      {tab === "brief" ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="label" htmlFor="cm-title">Titolo</label>
            <input id="cm-title" className="input" value={draft.title ?? ""}
              onChange={(e) => setDraft({ ...draft, title: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label" htmlFor="cm-surface">Surface</label>
              <select id="cm-surface" className="input" value={draft.surface} disabled={contributorLocked}
                onChange={(e) => setDraft({ ...draft, surface: e.target.value })}>
                {Object.entries(config?.surfaces ?? {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="cm-format">Format</label>
              <select id="cm-format" className="input" value={draft.format} disabled={contributorLocked}
                onChange={(e) => setDraft({ ...draft, format: e.target.value })}>
                <option value="">—</option>
                {Object.entries(config?.formats ?? {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label" htmlFor="cm-pillar">Pillar</label>
              <select id="cm-pillar" className="input" value={draft.pillar} disabled={contributorLocked}
                onChange={(e) => setDraft({ ...draft, pillar: e.target.value })}>
                <option value="">—</option>
                {Object.entries(config?.pillars ?? {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="cm-platform">Piattaforma</label>
              <select id="cm-platform" className="input" value={draft.platform} disabled={contributorLocked}
                onChange={(e) => setDraft({ ...draft, platform: e.target.value })}>
                {Object.entries(config?.platforms ?? {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label" htmlFor="cm-score">Score Critico (0-50, gate {gate})</label>
              <input id="cm-score" className="input font-mono" type="number" min={0} max={50}
                value={draft.critic_score ?? ""} disabled={contributorLocked}
                onChange={(e) => setDraft({ ...draft, critic_score: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="cm-sched">Programmato per</label>
              <input id="cm-sched" className="input font-mono" type="datetime-local"
                value={draft.scheduled_at ?? ""} disabled={contributorLocked}
                onChange={(e) => setDraft({ ...draft, scheduled_at: e.target.value })} />
            </div>
          </div>
          <div className="md:col-span-2">
            <label className="label" htmlFor="cm-hook">Hook (prime 3 secondi)</label>
            <input id="cm-hook" className="input" value={draft.hook ?? ""}
              onChange={(e) => setDraft({ ...draft, hook: e.target.value })} />
          </div>
          <div className="md:col-span-2">
            <label className="label" htmlFor="cm-script">Script</label>
            <textarea id="cm-script" className="input min-h-[140px]" value={draft.script ?? ""}
              onChange={(e) => setDraft({ ...draft, script: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="cm-cta">CTA keyword (DM)</label>
            <input id="cm-cta" className="input font-mono" value={draft.cta_keyword ?? ""}
              onChange={(e) => setDraft({ ...draft, cta_keyword: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="cm-url">URL pubblicato</label>
            <input id="cm-url" className="input font-mono text-xs" value={draft.external_url ?? ""}
              disabled={contributorLocked}
              onChange={(e) => setDraft({ ...draft, external_url: e.target.value })} />
          </div>
          <div className="md:col-span-2">
            <label className="label" htmlFor="cm-notes">Note di regia</label>
            <textarea id="cm-notes" className="input min-h-[70px]" value={draft.notes ?? ""}
              onChange={(e) => setDraft({ ...draft, notes: e.target.value })} />
          </div>
          <div className="md:col-span-2">
            <label className="label" htmlFor="cm-assets">Link asset (uno per riga — Higgsfield, Gamma…)</label>
            <textarea id="cm-assets" className="input min-h-[60px] font-mono text-xs" value={draft.asset_links ?? ""}
              onChange={(e) => setDraft({ ...draft, asset_links: e.target.value })} />
            {content.asset_links.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {content.asset_links.map((link) => (
                  <a key={link} href={link} target="_blank" rel="noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-gold-400 hover:text-gold-500 transition-colors">
                    <ExternalLink className="w-3 h-3" aria-hidden />
                    {new URL(link, "https://x.invalid").hostname}
                  </a>
                ))}
              </div>
            )}
          </div>
          <div className="md:col-span-2 flex justify-end">
            <button className="btn-gold" onClick={save} disabled={saving}>
              {saving ? "Salvataggio…" : "Salva"}
            </button>
          </div>
        </div>
      ) : (
        <div>
          {metrics.length === 0 ? (
            <p className="text-ink-500 text-sm mb-4">
              Nessuno snapshot. Le metriche vanno inserite entro 48h dalla pubblicazione.
            </p>
          ) : (
            <div className="overflow-x-auto mb-5">
              <table className="table-base">
                <thead>
                  <tr>
                    <th>Rilevato</th><th>Retention</th><th>Hook</th><th>Save rate</th>
                    <th>Share rate</th><th>ICP ratio</th><th>DM→FHS</th>
                    <th className="text-ink-500">Views</th><th className="text-ink-500">Likes</th>
                    {isEditor && <th aria-label="Azioni" />}
                  </tr>
                </thead>
                <tbody>
                  {metrics.map((m) => (
                    <tr key={m.id}>
                      <td className="font-mono text-xs">{fmtDateTime(m.captured_at)}</td>
                      <td className="kpi-number">{pct(m.avg_retention_pct)}</td>
                      <td className="kpi-number">{pct(m.hook_retention_pct)}</td>
                      <td className="kpi-number">{ratePct(m.save_rate)}</td>
                      <td className="kpi-number">{ratePct(m.share_rate)}</td>
                      <td className="kpi-number">{ratePct(m.icp_ratio, 0)}</td>
                      <td className="kpi-number">{ratePct(m.dm_fhs_rate, 0)}</td>
                      <td className="kpi-number text-ink-500">{num(m.views)}</td>
                      <td className="kpi-number text-ink-500">{num(m.likes)}</td>
                      {isEditor && (
                        <td>
                          <button
                            className="text-ink-500 hover:text-warn transition-colors cursor-pointer"
                            aria-label="Elimina snapshot"
                            onClick={async () => {
                              await api.delete(`/api/metrics/${m.id}`);
                              await load();
                              onChanged();
                            }}
                          >
                            <Trash2 className="w-4 h-4" aria-hidden />
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {isEditor && (
            <div>
              <h3 className="text-sm font-bold mb-3">Nuovo snapshot manuale</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {METRIC_INPUTS.map(({ key, label, step }) => (
                  <div key={String(key)}>
                    <label className="label" htmlFor={`m-${String(key)}`}>{label}</label>
                    <input
                      id={`m-${String(key)}`}
                      className="input font-mono"
                      type="number"
                      step={step ?? "1"}
                      value={metricDraft[String(key)] ?? ""}
                      onChange={(e) => setMetricDraft({ ...metricDraft, [String(key)]: e.target.value })}
                    />
                  </div>
                ))}
              </div>
              <div className="flex justify-end mt-4">
                <button className="btn-gold" onClick={addMetric}>
                  <Plus className="w-4 h-4" aria-hidden /> Aggiungi snapshot
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}
