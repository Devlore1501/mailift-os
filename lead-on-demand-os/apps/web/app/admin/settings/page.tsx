"use client";

import { useEffect, useState } from "react";
import { ErrorBox, Field, PageTitle, useApi } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface Setting { key: string; value: unknown }
interface Template { id: string; name: string; vertical: string; leadType: string; template: unknown; criteria: unknown; scoreConfig: unknown; active: boolean }

export default function SettingsPage() {
  const { user } = useAuth();
  const isSuper = user?.role === "SUPER_ADMIN";
  const { data: settings, reload } = useApi<Setting[]>("/settings");
  const { data: templates, reload: reloadT } = useApi<Template[]>("/qualification-templates");
  const [dedupe, setDedupe] = useState("90");
  const [selected, setSelected] = useState<Template | null>(null);
  const [json, setJson] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  useEffect(() => {
    const s = settings?.find((x) => x.key === "dedupe_window_days");
    if (s) setDedupe(String(s.value));
  }, [settings]);
  useEffect(() => {
    if (selected) setJson(JSON.stringify({ template: selected.template, criteria: selected.criteria, scoreConfig: selected.scoreConfig }, null, 2));
  }, [selected]);
  async function saveDedupe() {
    setErr(null);
    try {
      await api("/settings/dedupe_window_days", { method: "PUT", json: { value: Number(dedupe) } });
      setMsg("Finestra duplicati aggiornata.");
      reload();
    } catch (e) {
      setErr((e as Error).message);
    }
  }
  async function saveTemplate() {
    if (!selected) return;
    setErr(null);
    try {
      const parsed = JSON.parse(json);
      await api(`/qualification-templates/${selected.id}`, { method: "PUT", json: parsed });
      setMsg(`Template "${selected.name}" salvato.`);
      reloadT();
    } catch (e) {
      setErr((e as Error).message);
    }
  }
  return (
    <div className="space-y-6">
      <PageTitle title="Impostazioni" />
      <ErrorBox error={err} />
      {msg && <p className="text-sm text-emerald-700">{msg}</p>}
      <section className="card max-w-lg space-y-3">
        <h2 className="font-semibold">Duplicati</h2>
        <Field label="Finestra duplicati (giorni)" hint="Un lead con lo stesso telefono o email di un lead entrato in questa finestra viene scartato senza scalare pacchetti.">
          <select className="input" value={dedupe} onChange={(e) => setDedupe(e.target.value)} disabled={!isSuper}>
            {["30", "60", "90", "180"].map((d) => <option key={d} value={d}>{d} giorni</option>)}
            {!["30", "60", "90", "180"].includes(dedupe) && <option value={dedupe}>{dedupe} giorni</option>}
          </select>
        </Field>
        {isSuper && <button className="btn-primary" onClick={saveDedupe}>Salva</button>}
      </section>
      <section className="card space-y-3">
        <h2 className="font-semibold">Script di qualifica, criteri e score</h2>
        <p className="text-sm text-slate-600">Ogni verticale e tipologia ha un template: domande con salti condizionali, criteri obbligatori/preferenziali/di esclusione e regole di punteggio. Modificabili qui senza toccare codice.</p>
        <div className="flex flex-wrap gap-2">
          {templates?.map((t) => <button key={t.id} className={selected?.id === t.id ? "btn-primary" : "btn-secondary"} onClick={() => setSelected(t)}>{t.name}{!t.active && " (disattivo)"}</button>)}
        </div>
        {selected && (
          <>
            <textarea className="input font-mono text-xs" rows={28} value={json} onChange={(e) => setJson(e.target.value)} spellCheck={false} />
            <button className="btn-primary" onClick={saveTemplate}>Salva template</button>
          </>
        )}
      </section>
    </div>
  );
}
