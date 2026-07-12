// Vista calendario settimana/mese (FR-M1-06) sui contenuti programmati/pubblicati.
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import ContentModal from "@/components/ContentModal";
import { ErrorBox, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { toDateKey } from "@/lib/format";
import { useApp } from "@/state/AppContext";
import type { Content } from "@/types";

const PILLAR_DOT: Record<string, string> = {
  revenue_leak: "bg-warn",
  proof: "bg-ok",
  educational: "bg-sky-400",
  contrarian: "bg-purple-400",
  backstage: "bg-ink-500",
};

function startOfWeek(d: Date): Date {
  const out = new Date(d);
  out.setDate(d.getDate() - ((d.getDay() + 6) % 7)); // lunedì
  out.setHours(0, 0, 0, 0);
  return out;
}

export default function Calendar() {
  const { config } = useApp();
  const [mode, setMode] = useState<"week" | "month">("month");
  const [anchor, setAnchor] = useState(() => new Date());
  const [contents, setContents] = useState<Content[] | null>(null);
  const [error, setError] = useState("");
  const [openId, setOpenId] = useState<number | null>(null);

  const days: Date[] = useMemo(() => {
    if (mode === "week") {
      const start = startOfWeek(anchor);
      return Array.from({ length: 7 }, (_, i) => new Date(start.getTime() + i * 86400_000));
    }
    const first = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
    const start = startOfWeek(first);
    const cells: Date[] = [];
    for (let i = 0; i < 42; i++) cells.push(new Date(start.getTime() + i * 86400_000));
    return cells;
  }, [mode, anchor]);

  useEffect(() => {
    const from = new Date(days[0]);
    const to = new Date(days[days.length - 1]);
    to.setHours(23, 59, 59);
    const params = new URLSearchParams({
      scheduled_from: from.toISOString(),
      scheduled_to: to.toISOString(),
    });
    api.get<Content[]>(`/api/contents?${params}`)
      .then(setContents)
      .catch((e) => setError(e.message));
  }, [days]);

  const byDay = useMemo(() => {
    const map = new Map<string, Content[]>();
    for (const c of contents ?? []) {
      const iso = c.scheduled_at ?? c.published_at;
      if (!iso) continue;
      const key = toDateKey(new Date(iso));
      map.set(key, [...(map.get(key) ?? []), c]);
    }
    return map;
  }, [contents]);

  const shift = (dir: 1 | -1) => {
    const next = new Date(anchor);
    if (mode === "week") next.setDate(anchor.getDate() + 7 * dir);
    else next.setMonth(anchor.getMonth() + dir);
    setAnchor(next);
  };

  const monthLabel = anchor.toLocaleDateString("it-IT", { month: "long", year: "numeric" });
  const todayKey = toDateKey(new Date());

  if (error) return <ErrorBox message={error} />;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-extrabold tracking-tight">Calendario</h1>
        <div className="flex items-center gap-2">
          <div className="flex gap-1" role="group" aria-label="Vista">
            {(["week", "month"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`rounded-md px-3 py-1.5 text-xs font-semibold border transition-colors duration-200 cursor-pointer ${
                  mode === m
                    ? "bg-gold-500 text-navy-950 border-gold-500"
                    : "bg-navy-800 text-ink-300 border-navy-700 hover:border-gold-500/50"
                }`}
              >
                {m === "week" ? "Settimana" : "Mese"}
              </button>
            ))}
          </div>
          <button className="btn-ghost !p-2" onClick={() => shift(-1)} aria-label="Periodo precedente">
            <ChevronLeft className="w-4 h-4" aria-hidden />
          </button>
          <span className="text-sm font-semibold capitalize min-w-36 text-center">{monthLabel}</span>
          <button className="btn-ghost !p-2" onClick={() => shift(1)} aria-label="Periodo successivo">
            <ChevronRight className="w-4 h-4" aria-hidden />
          </button>
        </div>
      </div>

      {!contents ? (
        <Spinner />
      ) : (
        <div className="card overflow-hidden">
          <div className="grid grid-cols-7 border-b border-navy-700">
            {["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"].map((d) => (
              <div key={d} className="px-2 py-2 text-xs font-bold uppercase tracking-wider text-ink-500 text-center">
                {d}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-7">
            {days.map((day) => {
              const key = toDateKey(day);
              const items = byDay.get(key) ?? [];
              const inMonth = mode === "week" || day.getMonth() === anchor.getMonth();
              return (
                <div
                  key={key}
                  className={`border-b border-r border-navy-700/50 p-1.5 ${
                    mode === "week" ? "min-h-[45vh]" : "min-h-[110px]"
                  } ${inMonth ? "" : "opacity-40"}`}
                >
                  <div className={`text-xs font-mono mb-1 px-1 ${
                    key === todayKey ? "text-gold-400 font-bold" : "text-ink-500"
                  }`}>
                    {day.getDate()}
                  </div>
                  <div className="space-y-1">
                    {items.map((c) => (
                      <button
                        key={c.id}
                        onClick={() => setOpenId(c.id)}
                        className={`w-full text-left rounded-md px-1.5 py-1 text-[11px] leading-tight font-medium cursor-pointer transition-colors duration-200 border ${
                          c.status === "published"
                            ? "bg-navy-700/50 border-navy-600 text-ink-300 hover:border-gold-500/50"
                            : "bg-gold-500/10 border-gold-500/30 text-gold-400 hover:border-gold-500"
                        }`}
                        title={c.title || c.idea_title || `#${c.id}`}
                      >
                        <span className={`inline-block w-1.5 h-1.5 rounded-full mr-1 ${PILLAR_DOT[c.pillar ?? ""] ?? "bg-ink-500"}`} aria-hidden />
                        {(c.title || c.idea_title || `#${c.id}`).slice(0, 34)}
                        <span className="text-ink-500 block pl-3">
                          {config?.surfaces[c.surface]}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="flex gap-4 text-xs text-ink-500 flex-wrap">
        {Object.entries(config?.pillars ?? {}).map(([k, v]) => (
          <span key={k} className="inline-flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${PILLAR_DOT[k]}`} aria-hidden /> {v}
          </span>
        ))}
      </div>

      {openId !== null && (
        <ContentModal contentId={openId} onClose={() => setOpenId(null)} onChanged={() => setAnchor(new Date(anchor))} />
      )}
    </div>
  );
}
