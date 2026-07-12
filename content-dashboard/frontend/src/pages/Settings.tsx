// FR-X-03: target pillar, soglie winner/kill, fonti Idea Engine, utenti + activity log.
import { Plus, RefreshCw, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { EmptyState, ErrorBox, Modal, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { fmtDateTime } from "@/lib/format";
import { useApp } from "@/state/AppContext";
import type { Source, User } from "@/types";

interface CatalogEntry {
  type: string;
  label: string;
  url: string;
  note: string;
  installed: boolean;
}

const THRESHOLD_FIELDS: { key: string; label: string }[] = [
  { key: "critic_gate_min", label: "Gate Critico minimo (0-50)" },
  { key: "winner_retention_pct", label: "Winner: retention > %" },
  { key: "winner_save_rate_decile", label: "Winner: save rate ≥ percentile" },
  { key: "kill_retention_pct", label: "Kill: retention media < %" },
  { key: "kill_min_posts", label: "Kill: dopo almeno N post" },
  { key: "format_min_posts", label: "Giudizio format: minimo post" },
  { key: "pillar_mix_alert_pp", label: "Alert mix pillar (± punti %)" },
  { key: "metrics_reminder_hours", label: "Promemoria metriche (ore)" },
  { key: "idea_job_interval_hours", label: "Job Idea Engine ogni (ore)" },
];

export default function Settings() {
  const { config, reloadConfig, isAdmin, isEditor, user } = useApp();
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [targets, setTargets] = useState<Record<string, string>>({});
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [sources, setSources] = useState<Source[] | null>(null);
  const [catalog, setCatalog] = useState<CatalogEntry[]>([]);
  const [users, setUsers] = useState<User[] | null>(null);
  const [activity, setActivity] = useState<{ id: number; user: string | null; entity: string; action: string; at: string }[] | null>(null);
  const [newSource, setNewSource] = useState<{ type: string; url: string; label: string } | null>(null);
  const [newUser, setNewUser] = useState<{ name: string; email: string; password: string; role: string } | null>(null);

  useEffect(() => {
    if (!config) return;
    setTargets(Object.fromEntries(Object.entries(config.pillar_targets).map(([k, v]) => [k, String(v)])));
    setSettings({ ...config.settings });
  }, [config]);

  const loadLists = useCallback(async () => {
    const jobs: Promise<void>[] = [
      api.get<Source[]>("/api/sources").then(setSources),
      api.get<CatalogEntry[]>("/api/sources/catalog").then(setCatalog),
    ];
    if (isAdmin) jobs.push(api.get<User[]>("/api/users").then(setUsers));
    if (isEditor) jobs.push(api.get<typeof activity>("/api/activity?limit=50").then((a) => setActivity(a)));
    await Promise.all(jobs);
  }, [isAdmin, isEditor]);

  useEffect(() => {
    loadLists().catch((e) => setError(e.message));
  }, [loadLists]);

  const flash = (msg: string) => {
    setNotice(msg);
    setError("");
    window.setTimeout(() => setNotice(""), 3000);
  };

  const saveTargets = async () => {
    try {
      await api.put("/api/config/pillar-targets", {
        targets: Object.fromEntries(Object.entries(targets).map(([k, v]) => [k, Number(v)])),
      });
      await reloadConfig();
      flash("Target pillar salvati");
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const saveSettings = async () => {
    try {
      await api.put("/api/config/settings", {
        values: Object.fromEntries(THRESHOLD_FIELDS.map(({ key }) => [key, settings[key] ?? ""])),
      });
      await reloadConfig();
      flash("Soglie salvate");
    } catch (e) {
      setError((e as Error).message);
    }
  };

  if (!config) return <Spinner />;

  const targetSum = Object.values(targets).reduce((acc, v) => acc + (Number(v) || 0), 0);

  return (
    <div className="space-y-8 max-w-4xl">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight">Impostazioni</h1>
        <p className="text-sm text-ink-500">Accesso: {user?.role}</p>
      </div>

      {error && <ErrorBox message={error} />}
      {notice && <div className="rounded-lg border border-ok/40 bg-ok/10 text-ok px-3 py-2 text-sm">{notice}</div>}

      {/* target pillar */}
      <section className="card p-5" aria-label="Target mix pillar">
        <h2 className="font-bold mb-1">Mix pillar target</h2>
        <p className="text-xs text-ink-500 mb-4">La somma deve fare 100. Scostamenti oltre soglia generano alert in Overview.</p>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {Object.entries(config.pillars).map(([key, label]) => (
            <div key={key}>
              <label className="label" htmlFor={`t-${key}`}>{label}</label>
              <input id={`t-${key}`} className="input font-mono" type="number" min={0} max={100}
                value={targets[key] ?? ""} disabled={!isAdmin}
                onChange={(e) => setTargets({ ...targets, [key]: e.target.value })} />
            </div>
          ))}
        </div>
        <div className="flex items-center justify-between mt-4">
          <span className={`font-mono text-sm ${Math.abs(targetSum - 100) > 0.5 ? "text-warn" : "text-ok"}`}>
            Somma: {targetSum}%
          </span>
          {isAdmin && <button className="btn-gold" onClick={saveTargets}>Salva target</button>}
        </div>
      </section>

      {/* soglie */}
      <section className="card p-5" aria-label="Soglie">
        <h2 className="font-bold mb-1">Soglie winner / kill / gate</h2>
        <p className="text-xs text-ink-500 mb-4">Regole di decisione (§10 PRD). Modificabili solo dall'Admin.</p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {THRESHOLD_FIELDS.map(({ key, label }) => (
            <div key={key}>
              <label className="label" htmlFor={`s-${key}`}>{label}</label>
              <input id={`s-${key}`} className="input font-mono" value={settings[key] ?? ""}
                disabled={!isAdmin}
                onChange={(e) => setSettings({ ...settings, [key]: e.target.value })} />
            </div>
          ))}
        </div>
        {isAdmin && (
          <div className="flex justify-end mt-4">
            <button className="btn-gold" onClick={saveSettings}>Salva soglie</button>
          </div>
        )}
      </section>

      {/* fonti */}
      <section className="card p-5" aria-label="Fonti Idea Engine">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="font-bold">Fonti Idea Engine</h2>
            <p className="text-xs text-ink-500">Reddit, Google News/Trends, blog di settore, RSS, X via bridge. Job giornaliero automatico.</p>
          </div>
          {isAdmin && (
            <button className="btn-gold" onClick={() => setNewSource({ type: "rss", url: "", label: "" })}>
              <Plus className="w-4 h-4" aria-hidden /> Fonte
            </button>
          )}
        </div>
        {!sources ? (
          <Spinner />
        ) : sources.length === 0 ? (
          <EmptyState title="Nessuna fonte configurata" hint="Aggiungi almeno 2 fonti RSS per alimentare la coda idee." />
        ) : (
          <div className="overflow-x-auto">
            <table className="table-base">
              <thead>
                <tr><th>Label</th><th>Tipo</th><th>URL</th><th>Ultimo fetch</th><th>Stato</th>{isAdmin && <th />}</tr>
              </thead>
              <tbody>
                {sources.map((s) => (
                  <tr key={s.id}>
                    <td className="font-semibold">{s.label}</td>
                    <td className="font-mono text-xs">{s.type}</td>
                    <td className="font-mono text-xs max-w-56 truncate" title={s.url}>{s.url}</td>
                    <td className="font-mono text-xs">{fmtDateTime(s.last_fetched_at)}</td>
                    <td>
                      {!s.active ? (
                        <span className="text-xs text-ink-500">disattiva</span>
                      ) : s.last_error ? (
                        <span className="text-xs text-warn" title={s.last_error}>errore</span>
                      ) : (
                        <span className="text-xs text-ok">attiva</span>
                      )}
                    </td>
                    {isAdmin && (
                      <td>
                        <div className="flex gap-2">
                          <button className="text-ink-500 hover:text-ink-100 transition-colors cursor-pointer"
                            aria-label={s.active ? "Disattiva fonte" : "Attiva fonte"}
                            title={s.active ? "Disattiva" : "Attiva"}
                            onClick={async () => {
                              await api.patch(`/api/sources/${s.id}`, { active: !s.active });
                              await loadLists();
                            }}>
                            <RefreshCw className="w-4 h-4" aria-hidden />
                          </button>
                          <button className="text-ink-500 hover:text-warn transition-colors cursor-pointer"
                            aria-label="Elimina fonte"
                            onClick={async () => {
                              if (window.confirm(`Eliminare la fonte "${s.label}"?`)) {
                                await api.delete(`/api/sources/${s.id}`);
                                await loadLists();
                              }
                            }}>
                            <Trash2 className="w-4 h-4" aria-hidden />
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {!config.anthropic_configured && (
          <p className="text-xs text-warn mt-3">
            ANTHROPIC_API_KEY non configurata: il fetch funziona, la sintesi AI delle proposte è disattivata.
          </p>
        )}

        {/* catalogo fonti consigliate */}
        {catalog.some((c) => !c.installed) && (
          <div className="mt-5 pt-4 border-t border-navy-700">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold">Fonti consigliate</h3>
              {isAdmin && (
                <button className="btn-ghost !py-1.5" onClick={async () => {
                  try {
                    const res = await api.post<{ added: string[] }>("/api/sources/catalog/add", {});
                    flash(`${res.added.length} fonti aggiunte`);
                    await loadLists();
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}>
                  Aggiungi tutte
                </button>
              )}
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {catalog.filter((c) => !c.installed).map((entry) => (
                <div key={entry.url} className="flex items-center gap-3 rounded-lg border border-navy-700 bg-navy-900 px-3 py-2">
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-semibold truncate">
                      {entry.label}
                      <span className="font-mono text-[10px] text-ink-500 ml-2 uppercase">{entry.type}</span>
                    </div>
                    <div className="text-xs text-ink-500 truncate" title={entry.note}>{entry.note}</div>
                  </div>
                  {isAdmin && (
                    <button className="btn-ghost !py-1 !px-2.5 text-xs shrink-0" onClick={async () => {
                      try {
                        await api.post("/api/sources/catalog/add", { urls: [entry.url] });
                        await loadLists();
                      } catch (e) {
                        setError((e as Error).message);
                      }
                    }}>
                      <Plus className="w-3.5 h-3.5" aria-hidden /> Aggiungi
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
        <p className="text-xs text-ink-500 mt-3">
          X/Twitter non espone feed RSS pubblici: per seguire account o ricerche X aggiungi come fonte
          l'URL di un bridge (Nitter o RSSHub) con tipo «twitter».
        </p>
      </section>

      {/* utenti */}
      {isAdmin && (
        <section className="card p-5" aria-label="Utenti">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="font-bold">Utenti</h2>
              <p className="text-xs text-ink-500">Admin gestisce tutto · Editor opera il piano · Contributor scrive script e idee.</p>
            </div>
            <button className="btn-gold" onClick={() => setNewUser({ name: "", email: "", password: "", role: "contributor" })}>
              <Plus className="w-4 h-4" aria-hidden /> Utente
            </button>
          </div>
          {!users ? (
            <Spinner />
          ) : (
            <table className="table-base">
              <thead><tr><th>Nome</th><th>Email</th><th>Ruolo</th><th>Stato</th></tr></thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td className="font-semibold">{u.name}</td>
                    <td className="font-mono text-xs">{u.email}</td>
                    <td>
                      <select className="input !w-auto !py-1" value={u.role} aria-label={`Ruolo di ${u.name}`}
                        onChange={async (e) => {
                          await api.patch(`/api/users/${u.id}`, { role: e.target.value });
                          await loadLists();
                        }}>
                        {config.roles.map((r) => <option key={r} value={r}>{r}</option>)}
                      </select>
                    </td>
                    <td>
                      <button
                        className={`text-xs font-semibold cursor-pointer transition-colors ${u.active ? "text-ok hover:text-warn" : "text-ink-500 hover:text-ok"}`}
                        onClick={async () => {
                          await api.patch(`/api/users/${u.id}`, { active: !u.active });
                          await loadLists();
                        }}
                      >
                        {u.active ? "attivo" : "disattivato"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}

      {/* activity log */}
      {isEditor && activity && activity.length > 0 && (
        <section className="card p-5" aria-label="Attività recente">
          <h2 className="font-bold mb-3">Attività recente</h2>
          <ul className="space-y-1.5 text-sm">
            {activity.map((a) => (
              <li key={a.id} className="flex gap-3">
                <span className="font-mono text-xs text-ink-500 shrink-0 w-28">{fmtDateTime(a.at)}</span>
                <span className="text-ink-300">
                  <span className="font-semibold text-ink-100">{a.user ?? "sistema"}</span>{" "}
                  · {a.entity}: {a.action}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {newSource && (
        <Modal title="Nuova fonte" onClose={() => setNewSource(null)}>
          <div className="space-y-4">
            <div>
              <label className="label" htmlFor="ns-label">Label</label>
              <input id="ns-label" className="input" value={newSource.label}
                onChange={(e) => setNewSource({ ...newSource, label: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="ns-type">Tipo</label>
              <select id="ns-type" className="input" value={newSource.type}
                onChange={(e) => setNewSource({ ...newSource, type: e.target.value })}>
                {config.source_types.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="ns-url">URL feed</label>
              <input id="ns-url" className="input font-mono text-xs" value={newSource.url}
                placeholder="https://esempio.com/feed.xml · https://reddit.com/r/ecommerce/.rss"
                onChange={(e) => setNewSource({ ...newSource, url: e.target.value })} />
            </div>
            <div className="flex justify-end">
              <button className="btn-gold" disabled={!newSource.label || !newSource.url}
                onClick={async () => {
                  try {
                    await api.post("/api/sources", { ...newSource, active: true });
                    setNewSource(null);
                    await loadLists();
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}>
                Crea fonte
              </button>
            </div>
          </div>
        </Modal>
      )}

      {newUser && (
        <Modal title="Nuovo utente" onClose={() => setNewUser(null)}>
          <div className="space-y-4">
            <div>
              <label className="label" htmlFor="nu-name">Nome</label>
              <input id="nu-name" className="input" value={newUser.name}
                onChange={(e) => setNewUser({ ...newUser, name: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="nu-email">Email</label>
              <input id="nu-email" className="input" type="email" value={newUser.email}
                onChange={(e) => setNewUser({ ...newUser, email: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="nu-pass">Password (min 8 caratteri)</label>
              <input id="nu-pass" className="input" type="password" value={newUser.password}
                onChange={(e) => setNewUser({ ...newUser, password: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="nu-role">Ruolo</label>
              <select id="nu-role" className="input" value={newUser.role}
                onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}>
                {config.roles.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div className="flex justify-end">
              <button className="btn-gold"
                disabled={!newUser.name || !newUser.email || newUser.password.length < 8}
                onClick={async () => {
                  try {
                    await api.post("/api/users", newUser);
                    setNewUser(null);
                    await loadLists();
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}>
                Crea utente
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
