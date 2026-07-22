import { AlertTriangle, ExternalLink } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface BillToWarningProps {
  supplier: string;
  portalUrl?: string;
  className?: string;
}

/**
 * Amber warning icon shown in the Review table when the supplier's invoice
 * Bill to is not addressed to "Mailift Srl". The tooltip tells the user to fix
 * the billing address on the supplier's portal so future runs come out clean.
 */
export function BillToWarning({
  supplier,
  portalUrl,
  className,
}: BillToWarningProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className={cn(
            "inline-flex h-5 w-5 items-center justify-center rounded-full bg-warning/15 text-warning",
            className
          )}
          role="img"
          aria-label={`Warning Bill to per ${supplier}`}
        >
          <AlertTriangle className="h-3.5 w-3.5" />
        </span>
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-[280px] text-left">
        <div className="space-y-1">
          <p className="font-medium">Bill to non intestato a Mailift Srl</p>
          <p className="text-muted-foreground">
            La fattura di <span className="font-medium">{supplier}</span> ha un
            Bill to diverso. Correggi l'indirizzo di fatturazione sul portale
            del fornitore per eliminare il warning dai prossimi run.
          </p>
          {portalUrl && (
            <a
              href={portalUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 pt-1 text-primary underline-offset-2 hover:underline"
            >
              Apri portale <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      </TooltipContent>
    </Tooltip>
  );
}
