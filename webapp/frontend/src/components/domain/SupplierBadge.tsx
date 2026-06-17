import { Badge } from "@/components/ui/badge";
import { EU_COUNTRIES } from "@/lib/utils";

interface SupplierBadgeProps {
  countryIso?: string | null;
  className?: string;
}

/**
 * Country-aware badge for supplier listings. Color map:
 *   IT        → red    "🇮🇹 Italia"
 *   UE (non-IT) → blue "🇪🇺 UE"
 *   extra-UE  → purple "🌍 Extra-UE"
 *   unknown   → zinc   "?"
 * The raw ISO is shown alongside so users can double-check.
 */
export function SupplierBadge({ countryIso, className }: SupplierBadgeProps) {
  const iso = (countryIso || "").toUpperCase();

  if (!iso) {
    return (
      <Badge variant="zinc" className={className} title="Paese sconosciuto">
        ? Unknown
      </Badge>
    );
  }

  if (iso === "IT") {
    return (
      <Badge variant="red" className={className}>
        🇮🇹 Italia · {iso}
      </Badge>
    );
  }

  if (EU_COUNTRIES.has(iso)) {
    return (
      <Badge variant="blue" className={className}>
        🇪🇺 UE · {iso}
      </Badge>
    );
  }

  return (
    <Badge variant="purple" className={className}>
      🌍 Extra-UE · {iso}
    </Badge>
  );
}
