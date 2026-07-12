// Dashboard KPI (FR-M2-04/05) + mix pillar (FR-M1-08) + alert operativi.
// Gerarchia: segnali primari dominanti, vanity in grigio e marcate come tali.
import { AlertTriangle, TrendingUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ErrorBox, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { compactNum, fmtDate, pct, ratePct } from "@/lib/format";
import type { KpiOverview, PillarMix } from "@/types";

const PERIODS = [
  { label: "30 giorni", days: 30 },
  { label: "90 giorni", days: 90 },
  { label: "Tutto", days: 0 },
];

function KpiCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="card p-4">
      <div className="text-xs font-semibold uppercase tracking-wider text-ink-500">{label}</div>
      <div className="kpi-number text-3xl mt-1.5 text-ink-100">{value}</div>
      {hint && <div className="text-xs text-ink-500 mt-1">{hint}</div>}
    </div>
  );
}

export default function Overview() {
  const [days, setDays] = useState(30);
  const [data, setData] = useState<KpiOverview | null>(null);
  const [mix, setMix] = useState<PillarMix | null>(null);
  const [error, setError] = useState("");

  const query = useMemo(() => {
    if (!days) return "";
    const from = new Date(Date.now() - days * 86400_000).toISOString();
    return `?date_from=${encodeURIComponent(from)}`;
  }, [days]);

  useEffect(() => {
    setData(null);
    Promise.all([
      api.get<KpiOverview>(`/api/kpi/overview${query}`),
      api.get<PillarMix>(`/api/kpi/pillar-mix${query}`),
    ])
      .then(([ov, pm]) => {
        setData(ov);
        setMix(pm);
      })
      .catch((e) => setError(e.message));
  }, [query]);

  if (error) return <ErrorBox message={error} />;
  if (!data || !mix) return <Spinner />;

  const p = data.primary;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight">Overview</h1>
          <p className="text-sm text-ink-500">
            {data.n_published} pubblicati · {data.n_with_metrics} con metriche
          </p>
        </div>
        <div className="flex gap-1.5" role="group" aria-label="Periodo">
          {PERIODS.map((per) => (
            <button
              key={per.days}
              onClick={() => setDays(per.days)}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold border transition-colors duration-200 cursor-pointer ${
                days === per.days
                  ? "bg-gold-500 text-navy-950 border-gold-500"
                  : "bg-navy-800 text-ink-300 border-navy-700 hover:border-gold-500/50"
              }`}
            >
              {per.label}
            </button>
          ))}
        </div>
      </div>

      {/* alert operativi */}
      {(mix.alerts.length > 0 || data.missing_metrics.length > 0) && (
        <div className="space-y-2">
          {mix.alerts.map((a) => (
            <div key={a} className="flex items-center gap-2 rounded-lg border border-gold-500/40 bg-gold-500/10 text-gold-400 px-3 py-2 text-sm">
              <AlertTriangle className="w-4 h-4 shrink-0" aria-hidden />
              Mix pillar: {a}
            </div>
          ))}
          {data.missing_metrics.length > 0 && (
            <div className="flex items-center gap-2 rounded-lg border border-warn/40 bg-warn/10 text-warn px-3 py-2 text-sm">
              <AlertTriangle className="w-4 h-4 shrink-0" aria-hidden />
              {data.missing_metrics.length} contenut{data.missing_metrics.length === 1 ? "o" : "i"} oltre le 48h senza metriche:{" "}
              {data.missing_metrics.slice(0, 3).map((m) => m.title).join(", ")}
              {data.missing_metrics.length > 3 && "…"}
            </div>
          )}
        </div>
      )}

      {/* KPI primari — dominanti */}
      <section aria-label="KPI primari">
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
          <KpiCard label="Retention media" value={pct(p.avg_retention_pct)} hint="target >50%, ideale ~70%" />
          <KpiCard label="Hook retention" value={pct(p.hook_retention_pct)} hint=">80% ottimo" />
          <KpiCard label="Save rate" value={ratePct(p.save_rate)} hint="top-decile = winner" />
          <KpiCard label="Share rate" value={ratePct(p.share_rate)} />
          <KpiCard label="Composizione buyer" value={ratePct(p.icp_ratio, 0)} hint="quota ICP owner eCom" />
          <KpiCard
            label="DM → FHS"
            value={ratePct(p.dm_fhs_rate, 0)}
            hint={`${p.dm_keyword_triggers} DM · ${p.fhs_purchases} acquisti`}
          />
        </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* trend */}
        <section className="card p-4 lg:col-span-2" aria-label="Andamento settimanale">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-4 h-4 text-gold-500" aria-hidden />
            <h2 className="font-bold text-sm">Andamento settimanale</h2>
          </div>
          {data.trend.length === 0 ? (
            <p className="text-ink-500 text-sm py-8 text-center">Nessun contenuto pubblicato nel periodo.</p>
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.trend} margin={{ top: 5, right: 10, bottom: 0, left: -20 }}>
                  <CartesianGrid stroke="#1D2F52" strokeDasharray="3 3" />
                  <XAxis dataKey="week" stroke="#7D8DA3" fontSize={11} fontFamily="JetBrains Mono" />
                  <YAxis stroke="#7D8DA3" fontSize={11} fontFamily="JetBrains Mono" domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{ background: "#15233F", border: "1px solid #1D2F52", borderRadius: 8, fontSize: 12 }}
                    labelStyle={{ color: "#EAF0F8" }}
                    formatter={(value: number, name: string) =>
                      name.includes("rate") ? [`${(value * 100).toFixed(1)}%`, name] : [`${Number(value).toFixed(1)}%`, name]}
                  />
                  <Line type="monotone" dataKey="avg_retention_pct" name="Retention %" stroke="#E0A93B" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="hook_retention_pct" name="Hook %" stroke="#3DCB8F" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </section>

        {/* mix pillar */}
        <section className="card p-4" aria-label="Mix pillar">
          <h2 className="font-bold text-sm mb-3">Mix pillar reale vs target</h2>
          <div className="space-y-3">
            {mix.rows.map((row) => (
              <div key={row.pillar}>
                <div className="flex justify-between text-xs mb-1">
                  <span className={row.alert ? "text-gold-400 font-semibold" : "text-ink-300"}>
                    {row.label}
                  </span>
                  <span className="font-mono text-ink-500">
                    {row.real_pct.toFixed(0)}% / {row.target_pct.toFixed(0)}%
                    {row.alert && <span className="text-gold-400 ml-1">({row.delta_pp > 0 ? "+" : ""}{row.delta_pp}pp)</span>}
                  </span>
                </div>
                <div className="h-2 rounded-full bg-navy-900 overflow-hidden relative">
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${row.alert ? "bg-gold-500" : "bg-navy-600"}`}
                    style={{ width: `${Math.min(100, row.real_pct)}%` }}
                  />
                  <div
                    className="absolute top-0 h-full w-0.5 bg-ink-300/70"
                    style={{ left: `${Math.min(100, row.target_pct)}%` }}
                    title={`Target ${row.target_pct}%`}
                  />
                </div>
              </div>
            ))}
          </div>
          <p className="text-[11px] text-ink-500 mt-3">
            Su {mix.total} contenuti attivi · alert oltre ±{mix.alert_threshold_pp}pp
          </p>
        </section>
      </div>

      {/* vanity — secondaria, marcata */}
      <section className="card p-4 border-dashed" aria-label="Metriche vanity">
        <div className="text-xs font-semibold uppercase tracking-wider text-ink-500 mb-2">
          Vanity metrics — non guidano le decisioni
        </div>
        <div className="flex gap-8">
          <div>
            <div className="kpi-number text-xl text-ink-500">{compactNum(data.secondary.views)}</div>
            <div className="text-xs text-ink-500">views totali</div>
          </div>
          <div>
            <div className="kpi-number text-xl text-ink-500">{compactNum(data.secondary.likes)}</div>
            <div className="text-xs text-ink-500">likes totali</div>
          </div>
        </div>
      </section>

      {data.missing_metrics.length > 0 && (
        <p className="text-xs text-ink-500">
          Ultimo aggiornamento dati: {fmtDate(new Date().toISOString())}
        </p>
      )}
    </div>
  );
}
