export function fmtDate(v: string | Date | null | undefined, withTime = true): string {
  if (!v) return "";
  const d = typeof v === "string" ? new Date(v) : v;
  if (Number.isNaN(d.getTime())) return "";
  return new Intl.DateTimeFormat("it-IT", { timeZone: "Europe/Rome", day: "2-digit", month: "2-digit", year: "numeric", ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}) }).format(d);
}

export function fmtMoney(v: number | string | null | undefined): string {
  if (v === null || v === undefined || v === "") return "";
  const n = typeof v === "string" ? Number(v) : v;
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 2 }).format(n);
}

export function fmtNum(v: number | null | undefined, digits = 0): string {
  if (v === null || v === undefined) return "";
  return new Intl.NumberFormat("it-IT", { maximumFractionDigits: digits }).format(v);
}

export function fmtPct(v: number | null | undefined): string {
  if (v === null || v === undefined) return "";
  return `${(v * 100).toFixed(0)}%`;
}

export function fullName(l: { firstName?: string | null; lastName?: string | null }): string {
  return `${l.firstName ?? ""} ${l.lastName ?? ""}`.trim() || "(senza nome)";
}

export function toLocalInput(v: string | Date | null | undefined): string {
  if (!v) return "";
  const d = typeof v === "string" ? new Date(v) : v;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
