// M2 Performance: breakdown per format/pillar/surface (decisioni scale/kill),
// elenco pubblicati con winner, import CSV metriche.
import { Award, Upload } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import ContentModal from "@/components/ContentModal";
import { EmptyState, ErrorBox, KillBadge, Modal, Spinner, WinnerBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { compactNum, fmtDate, pct, ratePct } from "@/lib/format";
import { useApp } from "@/state/AppContext";
import type { Breakdown, Content } from "@/types";

type SortKey = "avg_retention_pct" | "hook_retention_pct" | "save_rate" | "share_rate" | "icp_ratio" | "n_posts";

export default function Performance() {
  const { config, isEditor } = useApp();
  const [by, setBy] = useState<"format" | "pillar" | "surface">("format");
  const [breakdown, setBreakdown] = useState<Breakdown | null>(null);
  const [contents, setContents] = useState<Content[] | null>(null);
  const [error, setError] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("avg_retention_pct");
  const [openId, setOpenId] = useState<number | null>(null);
  const [importOpen, setImportOpen] = useState(false);

  const load = useCallback(async () => {
    const [b, c] = await Promise.all([
      api.get<Breakdown>(`/api/kpi/breakdown?by=${by}`),
      api.get<Content[]>("/api/contents?status=published,archived"),
    ]);
    setBreakdown(b);
    setContents(c);
  }, [by]);

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, [load]);

  const sortedRows = useMemo(() => {
    if (!breakdown) return [];
    return [...breakdown.rows].sort((a, b) => {
      const av = a[sortKey] ?? -1;
      const bv = b[sortKey] ?? -1;
      return (bv as number) - (av as number);
    });
  }, [breakdown, sortKey]);

  if (error) return <ErrorBox message={error} />;
  if (!breakdown || !contents) return <Spinner />;

  const th = breakdown.thresholds;
  const header = (key: SortKey, label: string) => (
    <th>
      <button
        className={`cursor-pointer transition-colors hover:text-ink-300 uppercase tracking-wider text-xs font-semibold ${
          sortKey === key ? "text-gold-400" : ""
        }`}
        onClick={() => setSortKey(key)}
      >
        {label}{sortKey === key ? " ↓" : ""}
      </button>
    </th>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight">Performance</h1>
          <p className="text-sm text-ink-500">
            Un format si giudica su {th.format_min_posts}-{th.kill_min_posts} post, non sul singolo ·
            kill se retention &lt; {th.kill_retention_pct}% dopo ≥{th.kill_min_posts} post
          </p>
        </div>
        {isEditor && (
          <button className="btn-gold" onClick={() => setImportOpen(true)}>
            <Upload className="w-4 h-4" aria-hidden /> Import CSV
          </button>
        )}
      </div>

      <div className="flex gap-1.5" role="group" aria-label="Raggruppa per">
        {(["format", "pillar", "surface"] as const).map((k) => (
          <button
            key={k}
            onClick={() => setBy(k)}
            className={`rounded-md px-3 py-1.5 text-xs font-semibold border transition-colors duration-200 cursor-pointer capitalize ${
              by === k
                ? "bg-gold-500 text-navy-950 border-gold-500"
                : "bg-navy-800 text-ink-300 border-navy-700 hover:border-gold-500/50"
            }`}
          >
            Per {k}
          </button>
        ))}
      </div>

      <div className="card overflow-x-auto">
        <table className="table-base">
          <thead>
            <tr>
              <th>{by}</th>
              {header("n_posts", "Post")}
              {header("avg_retention_pct", "Retention")}
              {header("hook_retention_pct", "Hook")}
              {header("save_rate", "Save rate")}
              {header("share_rate", "Share rate")}
              {header("icp_ratio", "ICP ratio")}
              <th>DM→FHS</th>
              <th className="text-ink-500">Views</th>
              <th>Winner</th>
              <th>Giudizio</th>
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((row) => (
              <tr key={row.key}>
                <td className="font-semibold">{row.label}</td>
                <td className="kpi-number">{row.n_with_metrics}<span className="text-ink-500">/{row.n_posts}</span></td>
                <td className={`kpi-number ${
                  row.avg_retention_pct !== null && row.avg_retention_pct > th.winner_retention_pct ? "text-gold-400 font-bold" : ""
                }`}>{pct(row.avg_retention_pct)}</td>
                <td className="kpi-number">{pct(row.hook_retention_pct)}</td>
                <td className="kpi-number">{ratePct(row.save_rate)}</td>
                <td className="kpi-number">{ratePct(row.share_rate)}</td>
                <td className={`kpi-number ${
                  row.icp_ratio !== null && row.icp_ratio < 0.5 ? "text-warn" : ""
                }`}>{ratePct(row.icp_ratio, 0)}</td>
                <td className="kpi-number">{ratePct(row.dm_fhs_rate, 0)}</td>
                <td className="kpi-number text-ink-500">{compactNum(row.views)}</td>
                <td>
                  {row.winner_count > 0 && (
                    <span className="inline-flex items-center gap-1 text-gold-400 text-xs font-semibold">
                      <Award className="w-3.5 h-3.5" aria-hidden /> {row.winner_count}
                    </span>
                  )}
                </td>
                <td>
                  {row.kill_flag ? (
                    <KillBadge />
                  ) : row.insufficient_sample ? (
                    <span className="text-[11px] text-ink-500">campione &lt; {th.format_min_posts}</span>
                  ) : (
                    <span className="text-[11px] text-ok">ok</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {sortedRows.length === 0 && (
          <EmptyState title="Nessun contenuto pubblicato" hint="I KPI si popolano dopo la pubblicazione e l'inserimento metriche." />
        )}
      </div>

      {/* contenuti pubblicati */}
      <section aria-label="Contenuti pubblicati">
        <h2 className="font-bold text-sm uppercase tracking-wider text-ink-500 mb-3">
          Contenuti pubblicati ({contents.length})
        </h2>
        <div className="card overflow-x-auto">
          <table className="table-base">
            <thead>
              <tr>
                <th>Contenuto</th><th>Pillar</th><th>Format</th><th>Pubblicato</th>
                <th>Retention</th><th>Save rate</th><th>ICP</th>
                <th className="text-ink-500">Views</th><th />
              </tr>
            </thead>
            <tbody>
              {contents.map((c) => (
                <tr key={c.id} className="cursor-pointer" onClick={() => setOpenId(c.id)}>
                  <td className="font-semibold max-w-72 truncate">
                    {c.title || c.idea_title || `#${c.id}`}
                  </td>
                  <td>{config?.pillars[c.pillar ?? ""] ?? "—"}</td>
                  <td className="text-ink-300">{config?.formats[c.format ?? ""] ?? "—"}</td>
                  <td className="font-mono text-xs">{fmtDate(c.published_at)}</td>
                  <td className="kpi-number">{pct(c.latest_metric?.avg_retention_pct ?? null)}</td>
                  <td className="kpi-number">{ratePct(c.latest_metric?.save_rate ?? null)}</td>
                  <td className="kpi-number">{ratePct(c.latest_metric?.icp_ratio ?? null, 0)}</td>
                  <td className="kpi-number text-ink-500">{compactNum(c.latest_metric?.views ?? null)}</td>
                  <td>{c.is_winner && <WinnerBadge />}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {contents.length === 0 && <EmptyState title="Ancora nessun contenuto pubblicato" />}
        </div>
      </section>

      {openId !== null && (
        <ContentModal contentId={openId} onClose={() => setOpenId(null)} onChanged={() => load()} />
      )}
      {importOpen && <ImportCsvModal onClose={() => setImportOpen(false)} onDone={() => load()} />}
    </div>
  );
}

// ---- Import CSV con mapping colonne (FR-M2-02) ----

function ImportCsvModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [columns, setColumns] = useState<string[]>([]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [matchField, setMatchField] = useState("external_url");
  const [matchColumn, setMatchColumn] = useState("");
  const [fields, setFields] = useState<string[]>([]);
  const [result, setResult] = useState<{ imported: number; unmatched: { row: number; key: string; reason: string }[]; errors: unknown[] } | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get<{ fields: string[] }>("/api/metrics/fields").then((r) => setFields(r.fields)).catch(() => {});
  }, []);

  const pickFile = async (f: File) => {
    setFile(f);
    setResult(null);
    const text = await f.text();
    const firstLine = text.split(/\r?\n/)[0] ?? "";
    const delim = firstLine.split(";").length > firstLine.split(",").length ? ";" : ",";
    const cols = firstLine.split(delim).map((c) => c.trim().replace(/^"|"$/g, "")).filter(Boolean);
    setColumns(cols);
    setMatchColumn(cols[0] ?? "");
    setMapping({});
  };

  const submit = async () => {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.set("file", file);
      form.set("mapping", JSON.stringify(Object.fromEntries(Object.entries(mapping).filter(([, v]) => v))));
      form.set("match_field", matchField);
      form.set("match_column", matchColumn);
      const res = await api.postForm<typeof result>("/api/metrics/import", form);
      setResult(res);
      onDone();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="Import CSV metriche" onClose={onClose} wide>
      <div className="space-y-4">
        <div>
          <label className="label" htmlFor="csv-file">File CSV (export piattaforma)</label>
          <input
            id="csv-file" type="file" accept=".csv,text/csv" className="input"
            onChange={(e) => e.target.files?.[0] && pickFile(e.target.files[0])}
          />
        </div>

        {columns.length > 0 && (
          <>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label" htmlFor="csv-matchfield">Aggancia contenuto per</label>
                <select id="csv-matchfield" className="input" value={matchField}
                  onChange={(e) => setMatchField(e.target.value)}>
                  <option value="external_url">URL pubblicato</option>
                  <option value="content_id">ID contenuto</option>
                  <option value="title">Titolo</option>
                </select>
              </div>
              <div>
                <label className="label" htmlFor="csv-matchcol">Colonna CSV con la chiave</label>
                <select id="csv-matchcol" className="input" value={matchColumn}
                  onChange={(e) => setMatchColumn(e.target.value)}>
                  {columns.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
            </div>
            <div>
              <span className="label">Mapping colonne → metriche</span>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {columns.filter((c) => c !== matchColumn).map((col) => (
                  <div key={col} className="flex items-center gap-2">
                    <span className="font-mono text-xs text-ink-300 w-40 truncate" title={col}>{col}</span>
                    <select className="input" value={mapping[col] ?? ""} aria-label={`Campo per colonna ${col}`}
                      onChange={(e) => setMapping({ ...mapping, [col]: e.target.value })}>
                      <option value="">ignora</option>
                      {fields.map((f) => <option key={f} value={f}>{f}</option>)}
                    </select>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {error && <ErrorBox message={error} />}
        {result && (
          <div className="rounded-lg border border-ok/40 bg-ok/10 px-3 py-2 text-sm text-ok">
            {result.imported} righe importate
            {result.unmatched.length > 0 && (
              <span className="text-warn block mt-1">
                {result.unmatched.length} non abbinate: {result.unmatched.slice(0, 5).map((u) => u.key || `riga ${u.row}`).join(", ")}
              </span>
            )}
          </div>
        )}

        <div className="flex justify-end">
          <button className="btn-gold" onClick={submit}
            disabled={busy || !file || Object.values(mapping).filter(Boolean).length === 0}>
            {busy ? "Import…" : "Importa"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
