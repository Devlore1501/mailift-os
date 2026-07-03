import { FlaskConical } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { BrandSwitcher } from "@/components/layout/BrandSwitcher";
import { useSystemStatus } from "@/lib/queries";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface TopBarProps {
  brandId: number | null;
}

export function TopBar({ brandId }: TopBarProps) {
  const { data: system } = useSystemStatus();

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-border/60 bg-background/80 px-6 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <span className="hidden text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground sm:block">
          Agenzia Mailift
        </span>
      </div>

      <div className="flex items-center gap-3">
        {system?.mock_mode && (
          <Tooltip>
            <TooltipTrigger asChild>
              <span>
                <Badge
                  variant="outline"
                  className="gap-1 border-amber-300 bg-amber-50 text-amber-700"
                >
                  <FlaskConical className="h-3 w-3" />
                  Modalità demo
                </Badge>
              </span>
            </TooltipTrigger>
            <TooltipContent>
              API Claude non configurata: generazione demo
            </TooltipContent>
          </Tooltip>
        )}
        <Separator orientation="vertical" className="h-6" />
        <BrandSwitcher currentBrandId={brandId} />
      </div>
    </header>
  );
}
