// M3 coda review proposte AI + M1 idee madri con repurposing view (FR-M1-03).
import { Check, ExternalLink, Lightbulb, Plus, Sparkles, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import ContentModal from "@/components/ContentModal";
import { EmptyState, ErrorBox, Modal, PillarBadge, ScoreBadge, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useApp } from "@/state/AppContext";
import type { Idea } from "@/types";

const DEFAULT_CHILDREN = [
  { surface: "reel", format: "" },
  { surface: "carousel", format: "" },
  { surface: "story", format: "" },
  { surface: "reel", format: "" },
];

export default function Ideas() {
  const { config, isEditor } = useApp();
  const [proposals, setProposals] = useState<Idea[] | null>(null);
  const [ideas, setIdeas] = useState<Idea[] | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [running, setRunning] = useState(false);
  const [brainstorming, setBrainstorming] = useState(false);
  const [newIdeaOpen, setNewIdeaOpen] = useState(false);
  const [childrenFor, setChildrenFor] = useState<Idea | null>(null);
  const [openContent, setOpenContent] = useState<number | null>(null);
  const [draft, setDraft] = useState({ title: "", angle: "", pillar: "", hook_draft: "" });
  const [childSpecs, setChildSpecs] = useState(DEFAULT_CHILDREN);

  const gate = Number(config?.settings.critic_gate_min ?? 38);

  const load = useCallback(async () => {
    const [p, a] = await Promise.all([
      api.get<Idea[]>("/api/ideas?status=proposed"),
      api.get<Idea[]>("/api/ideas?status=approved"),
    ]);
    setProposals(p);
    setIdeas(a);
  }, []);

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, [load]);

  const runEngine = async () => {
    setRunning(true);
    setError("");
    setNotice("");
    try {
      const res = await api.post<{ fetch: { total_added: number }; synthesis: { proposals_created?: number; error?: string } }>("/api/idea-engine/run");
      if (res.synthesis.error) setError(res.synthesis.error);
      else setNotice(`Fetch: ${res.fetch.total_added} nuovi item · ${res.synthesis.proposals_created ?? 0} proposte generate`);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  };

  const brainstorm = async () => {
    setBrainstorming(true);
    setError("");
    setNotice("");
    try {
      const res = await api.post<{ proposals_created: number; error?: string }>("/api/idea-engine/brainstorm?n=6");
      if (res.error) setError(res.error);
      else setNotice(`${res.proposals_created} spunti evergreen proposti — in coda review`);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBrainstorming(false);
    }
  };

  const decide = async (idea: Idea, status: "approved" | "discarded") => {
    await api.patch(`/api/ideas/${idea.id}`, { status });
    await load();
  };

  const createIdea = async () => {
    if (!draft.title.trim()) return;
    await api.post("/api/ideas", {
      title: draft.title,
      angle: draft.angle || null,
      pillar: draft.pillar || null,
      hook_draft: draft.hook_draft || null,
    });
    setDraft({ title: "", angle: "", pillar: "", hook_draft: "" });
    setNewIdeaOpen(false);
    await load();
  };

  const generateChildren = async () => {
    if (!childrenFor) return;
    await api.post(`/api/ideas/${childrenFor.id}/children`, {
      children: childSpecs.map((s) => ({ surface: s.surface, format: s.format || null })),
    });
    setChildrenFor(null);
    setChildSpecs(DEFAULT_CHILDREN);
    await load();
  };

  if (error && !proposals) return <ErrorBox message={error} />;
  if (!proposals || !ideas) return <Spinner />;

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight">Idee</h1>
          <p className="text-sm text-ink-500">1 idea madre a settimana → ~4 output collegati</p>
        </div>
        <div className="flex gap-2">
          {isEditor && (
            <>
              <button className="btn-ghost" onClick={runEngine} disabled={running}
                title="Fetch dalle fonti (Reddit, news, blog) + sintesi AI">
                <Sparkles className="w-4 h-4 text-gold-500" aria-hidden />
                {running ? "In corso…" : "Dalle fonti"}
              </button>
              <button className="btn-ghost" onClick={brainstorm} disabled={brainstorming}
                title="Argomenti interessanti da trattare, non legati alle notizie">
                <Lightbulb className="w-4 h-4 text-gold-500" aria-hidden />
                {brainstorming ? "In corso…" : "Spunti evergreen"}
              </button>
            </>
          )}
          <button className="btn-gold" onClick={() => setNewIdeaOpen(true)}>
            <Plus className="w-4 h-4" aria-hidden /> Idea madre
          </button>
        </div>
      </div>

      {error && <ErrorBox message={error} />}
      {notice && (
        <div className="rounded-lg border border-ok/40 bg-ok/10 text-ok px-3 py-2 text-sm">{notice}</div>
      )}

      {/* Coda review proposte AI (FR-M3-04) */}
      <section aria-label="Coda review proposte">
        <h2 className="font-bold text-sm uppercase tracking-wider text-ink-500 mb-3">
          Coda review — proposte AI ({proposals.length})
        </h2>
        {proposals.length === 0 ? (
          <div className="card">
            <EmptyState
              title="Nessuna proposta in coda"
              hint={config?.anthropic_configured
                ? "Esegui l'Idea Engine o attendi il job giornaliero."
                : "Configura ANTHROPIC_API_KEY nel .env per attivare la sintesi AI."}
            />
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {proposals.map((p) => (
              <div key={p.id} className="card p-4 flex flex-col">
                <div className="flex items-start justify-between gap-2">
                  <span className="font-mono text-xs bg-gold-500/15 text-gold-400 rounded-md px-1.5 py-0.5 shrink-0">
                    {p.relevance_score ?? "–"}/10
                  </span>
                  <PillarBadge pillar={p.pillar} label={config?.pillars[p.pillar ?? ""]} />
                </div>
                <h3 className="font-semibold mt-2 leading-snug">{p.title}</h3>
                {p.angle && <p className="text-sm text-ink-300 mt-1">{p.angle}</p>}
                {p.hook_draft && (
                  <p className="text-xs text-ink-500 mt-2 italic">Hook: “{p.hook_draft}”</p>
                )}
                {p.source_item && (
                  <a href={p.source_item.url} target="_blank" rel="noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-gold-400 hover:text-gold-500 mt-2 transition-colors">
                    <ExternalLink className="w-3 h-3" aria-hidden /> Fonte: {p.source_item.title.slice(0, 50)}
                  </a>
                )}
                {isEditor && (
                  <div className="flex gap-2 mt-4 pt-3 border-t border-navy-700">
                    <button className="btn-gold flex-1 justify-center" onClick={() => decide(p, "approved")}>
                      <Check className="w-4 h-4" aria-hidden /> Approva
                    </button>
                    <button className="btn-danger" onClick={() => decide(p, "discarded")} aria-label="Scarta">
                      <X className="w-4 h-4" aria-hidden />
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Repurposing view (FR-M1-03) */}
      <section aria-label="Idee madri">
        <h2 className="font-bold text-sm uppercase tracking-wider text-ink-500 mb-3">
          Idee madri ({ideas.length})
        </h2>
        {ideas.length === 0 ? (
          <div className="card"><EmptyState title="Nessuna idea madre" hint="Creane una o approva una proposta." /></div>
        ) : (
          <div className="space-y-3">
            {ideas.map((idea) => (
              <div key={idea.id} className="card p-4">
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-bold">{idea.title}</h3>
                      <PillarBadge pillar={idea.pillar} label={config?.pillars[idea.pillar ?? ""]} />
                      {idea.origin === "ai" && (
                        <span className="inline-flex items-center gap-1 text-[11px] text-gold-400">
                          <Sparkles className="w-3 h-3" aria-hidden /> Idea Engine
                        </span>
                      )}
                    </div>
                    {idea.angle && <p className="text-sm text-ink-300 mt-1">{idea.angle}</p>}
                  </div>
                  {isEditor && (
                    <button className="btn-ghost shrink-0" onClick={() => setChildrenFor(idea)}>
                      <Plus className="w-4 h-4" aria-hidden /> Genera output
                    </button>
                  )}
                </div>
                {idea.contents.length > 0 && (
                  <div className="flex gap-2 mt-3 flex-wrap">
                    {idea.contents.map((c) => (
                      <button
                        key={c.id}
                        onClick={() => setOpenContent(c.id)}
                        className="rounded-lg border border-navy-700 bg-navy-900 px-3 py-2 text-left cursor-pointer hover:border-gold-500/50 transition-colors duration-200"
                      >
                        <div className="text-xs font-semibold">
                          {config?.surfaces[c.surface]}
                          {c.format ? ` · ${config?.formats[c.format]}` : ""}
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-[11px] text-ink-500">{config?.status_labels[c.status]}</span>
                          <ScoreBadge score={c.critic_score} gate={gate} />
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {newIdeaOpen && (
        <Modal title="Nuova idea madre" onClose={() => setNewIdeaOpen(false)}>
          <div className="space-y-4">
            <div>
              <label className="label" htmlFor="ni-title">Titolo *</label>
              <input id="ni-title" className="input" value={draft.title}
                onChange={(e) => setDraft({ ...draft, title: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="ni-angle">Angolo</label>
              <textarea id="ni-angle" className="input min-h-[70px]" value={draft.angle}
                onChange={(e) => setDraft({ ...draft, angle: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="ni-pillar">Pillar</label>
              <select id="ni-pillar" className="input" value={draft.pillar}
                onChange={(e) => setDraft({ ...draft, pillar: e.target.value })}>
                <option value="">—</option>
                {Object.entries(config?.pillars ?? {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="ni-hook">Bozza hook</label>
              <input id="ni-hook" className="input" value={draft.hook_draft}
                onChange={(e) => setDraft({ ...draft, hook_draft: e.target.value })} />
            </div>
            <div className="flex justify-end">
              <button className="btn-gold" onClick={createIdea} disabled={!draft.title.trim()}>Crea</button>
            </div>
          </div>
        </Modal>
      )}

      {childrenFor && (
        <Modal title={`Genera output — ${childrenFor.title}`} onClose={() => setChildrenFor(null)}>
          <p className="text-sm text-ink-500 mb-4">
            Repurposing: dall'idea madre a più output su surface e format diversi.
          </p>
          <div className="space-y-3">
            {childSpecs.map((spec, i) => (
              <div key={i} className="flex gap-2 items-center">
                <span className="font-mono text-xs text-ink-500 w-5">{i + 1}.</span>
                <select className="input" value={spec.surface} aria-label={`Surface output ${i + 1}`}
                  onChange={(e) => setChildSpecs(childSpecs.map((s, j) => (j === i ? { ...s, surface: e.target.value } : s)))}>
                  {Object.entries(config?.surfaces ?? {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
                <select className="input" value={spec.format} aria-label={`Format output ${i + 1}`}
                  onChange={(e) => setChildSpecs(childSpecs.map((s, j) => (j === i ? { ...s, format: e.target.value } : s)))}>
                  <option value="">Format —</option>
                  {Object.entries(config?.formats ?? {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
                <button
                  className="text-ink-500 hover:text-warn transition-colors cursor-pointer shrink-0"
                  aria-label={`Rimuovi output ${i + 1}`}
                  onClick={() => setChildSpecs(childSpecs.filter((_, j) => j !== i))}
                >
                  <X className="w-4 h-4" aria-hidden />
                </button>
              </div>
            ))}
          </div>
          <div className="flex justify-between mt-4">
            <button className="btn-ghost" onClick={() => setChildSpecs([...childSpecs, { surface: "reel", format: "" }])}>
              <Plus className="w-4 h-4" aria-hidden /> Aggiungi output
            </button>
            <button className="btn-gold" onClick={generateChildren} disabled={childSpecs.length === 0}>
              Genera {childSpecs.length} output
            </button>
          </div>
        </Modal>
      )}

      {openContent !== null && (
        <ContentModal contentId={openContent} onClose={() => setOpenContent(null)} onChanged={() => load()} />
      )}
    </div>
  );
}
