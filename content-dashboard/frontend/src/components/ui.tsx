// Componenti UI di base condivisi.
import { AlertTriangle, Award, Loader2, Skull, X } from "lucide-react";
import { ReactNode, useEffect } from "react";

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-ink-500 text-sm py-8 justify-center">
      <Loader2 className="w-4 h-4 animate-spin" aria-hidden />
      {label ?? "Caricamento…"}
    </div>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-warn/40 bg-warn/10 text-warn px-3 py-2 text-sm" role="alert">
      <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" aria-hidden />
      <span>{message}</span>
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="text-center py-10">
      <p className="text-ink-300 font-semibold">{title}</p>
      {hint && <p className="text-ink-500 text-sm mt-1">{hint}</p>}
    </div>
  );
}

const PILLAR_COLORS: Record<string, string> = {
  revenue_leak: "bg-warn/15 text-warn border-warn/30",
  proof: "bg-ok/15 text-ok border-ok/30",
  educational: "bg-sky-400/15 text-sky-300 border-sky-400/30",
  contrarian: "bg-purple-400/15 text-purple-300 border-purple-400/30",
  backstage: "bg-ink-500/15 text-ink-300 border-ink-500/30",
};

export function PillarBadge({ pillar, label }: { pillar: string | null; label?: string }) {
  if (!pillar) return <span className="text-ink-500 text-xs">—</span>;
  return (
    <span className={`inline-block rounded-md border px-1.5 py-0.5 text-[11px] font-semibold ${PILLAR_COLORS[pillar] ?? PILLAR_COLORS.backstage}`}>
      {label ?? pillar}
    </span>
  );
}

export function ScoreBadge({ score, gate }: { score: number | null; gate: number }) {
  if (score === null) return <span className="text-ink-500 text-xs font-mono">—/50</span>;
  const ok = score >= gate;
  return (
    <span
      className={`font-mono text-xs font-semibold px-1.5 py-0.5 rounded-md ${
        ok ? "bg-ok/15 text-ok" : "bg-warn/15 text-warn"
      }`}
      title={ok ? "Sopra il gate Critico" : `Sotto il gate Critico (${gate})`}
    >
      {score}/50
    </span>
  );
}

export function WinnerBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-md bg-gold-500/15 border border-gold-500/40 text-gold-400 px-1.5 py-0.5 text-[11px] font-semibold">
      <Award className="w-3 h-3" aria-hidden /> Winner
    </span>
  );
}

export function KillBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-md bg-warn/15 border border-warn/40 text-warn px-1.5 py-0.5 text-[11px] font-semibold">
      <Skull className="w-3 h-3" aria-hidden /> Sotto soglia
    </span>
  );
}

export function Modal({
  title,
  onClose,
  children,
  wide,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-navy-950/80 backdrop-blur-sm p-4 overflow-y-auto"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div className={`card w-full ${wide ? "max-w-4xl" : "max-w-xl"} mt-8 mb-8`}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-navy-700">
          <h2 className="font-bold text-lg">{title}</h2>
          <button className="btn-ghost !p-2" onClick={onClose} aria-label="Chiudi">
            <X className="w-4 h-4" aria-hidden />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}
