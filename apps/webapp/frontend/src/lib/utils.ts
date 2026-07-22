import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * EU country ISO codes (matches tools/fic_client.py _EU_COUNTRIES).
 * Used to classify suppliers as IT / UE / extra-UE for badges and tax logic.
 */
export const EU_COUNTRIES = new Set<string>([
  "IT", "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
  "HU", "IE", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
]);

export function isEu(iso: string | null | undefined): boolean {
  if (!iso) return false;
  return EU_COUNTRIES.has(iso.toUpperCase());
}

export function isExtraUe(iso: string | null | undefined): boolean {
  if (!iso) return false;
  return !EU_COUNTRIES.has(iso.toUpperCase());
}

export function isItaly(iso: string | null | undefined): boolean {
  return (iso || "").toUpperCase() === "IT";
}

/**
 * Format amount as italian currency (e.g. "€ 3.112,45").
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

export function truncate(str: string, max: number): string {
  if (!str) return "";
  if (str.length <= max) return str;
  return str.slice(0, max - 1).trimEnd() + "…";
}
