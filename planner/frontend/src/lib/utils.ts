import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format amount as italian currency (e.g. "€ 14,50").
 */
export function formatCurrency(
  amount: number | null | undefined,
  currency = "EUR"
): string {
  if (amount == null || Number.isNaN(amount)) return "—";
  try {
    return new Intl.NumberFormat("it-IT", {
      style: "currency",
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    return `${amount.toFixed(2)} ${currency}`;
  }
}

/**
 * Format ISO date string for italian locale.
 * style="short" -> "08/04/2026"; style="medium" (default) -> "8 apr 2026"
 */
export function formatDate(
  iso: string | Date | null | undefined,
  style: "short" | "medium" | "long" = "medium"
): string {
  if (!iso) return "—";
  const d = typeof iso === "string" ? new Date(iso) : iso;
  if (Number.isNaN(d.getTime())) return "—";
  if (style === "short") {
    return new Intl.DateTimeFormat("it-IT", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    }).format(d);
  }
  if (style === "long") {
    return new Intl.DateTimeFormat("it-IT", {
      day: "numeric",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(d);
  }
  return new Intl.DateTimeFormat("it-IT", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(d);
}

/**
 * Format a percentage ratio (0.41 -> "41%").
 */
export function formatPercent(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("it-IT", {
    style: "percent",
    minimumFractionDigits: 0,
    maximumFractionDigits: 1,
  }).format(value);
}

/**
 * Next Monday (or today if today is Monday) as "YYYY-MM-DD".
 */
export function nextMonday(from = new Date()): string {
  const d = new Date(from);
  const day = d.getDay(); // 0 = sunday, 1 = monday
  const delta = day === 1 ? 7 : (8 - day) % 7 || 7;
  d.setDate(d.getDate() + delta);
  return d.toISOString().slice(0, 10);
}

export function truncate(str: string, max: number): string {
  if (!str) return "";
  if (str.length <= max) return str;
  return str.slice(0, max - 1).trimEnd() + "…";
}

/** Primo giorno del mese prossimo, ISO YYYY-MM-01. */
export function nextMonthStart(from = new Date()): string {
  const d = new Date(from.getFullYear(), from.getMonth() + 1, 1);
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  return `${d.getFullYear()}-${mm}-01`;
}

/** "2026-08-01" → "agosto 2026". */
export function formatMonth(monthStart: string): string {
  const d = new Date(monthStart + "T00:00:00");
  return d.toLocaleDateString("it-IT", { month: "long", year: "numeric" });
}
