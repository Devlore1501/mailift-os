import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface VatBadgeProps {
  vatId: number;
  vatRatePercent?: number;
  className?: string;
}

interface VatMeta {
  label: string;
  tooltip: string;
  variant: "blue" | "purple" | "amber" | "zinc";
}

function resolveVatMeta(vatId: number, vatRatePercent?: number): VatMeta {
  // Match tools/fic_client.get_vat_id_for_autofattura logic
  if (vatId === 0) {
    return {
      label: "22% RC",
      tooltip: "Reverse charge art. 7-ter UE",
      variant: "blue",
    };
  }
  if (vatId === 10) {
    return {
      label: "0% NS",
      tooltip: "Operazione non soggetta art. 7-ter extra-UE",
      variant: "purple",
    };
  }
  if (vatId === 11) {
    return {
      label: "0% IC",
      tooltip: "Inversione contabile art. 7-ter",
      variant: "amber",
    };
  }
  const rate =
    vatRatePercent != null && !Number.isNaN(vatRatePercent)
      ? vatRatePercent
      : 0;
  return {
    label: `${rate}%`,
    tooltip: `Aliquota IVA ${rate}% (vat_id ${vatId})`,
    variant: "zinc",
  };
}

/**
 * Badge for the VAT column in the review table.
 * Shows a compact code + tooltip describing the legal basis.
 */
export function VatBadge({ vatId, vatRatePercent, className }: VatBadgeProps) {
  const meta = resolveVatMeta(vatId, vatRatePercent);
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="inline-flex">
          <Badge variant={meta.variant} className={className}>
            {meta.label}
          </Badge>
        </span>
      </TooltipTrigger>
      <TooltipContent side="top">{meta.tooltip}</TooltipContent>
    </Tooltip>
  );
}
