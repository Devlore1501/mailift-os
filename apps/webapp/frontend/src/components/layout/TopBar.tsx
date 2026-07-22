import { useLocation, Link } from "react-router-dom";
import { ChevronRight, Command as CommandIcon } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { EnvironmentSwitch } from "@/components/domain/EnvironmentSwitch";
import { cn } from "@/lib/utils";

const ROUTE_LABELS: Record<string, string> = {
  "": "Dashboard",
  new: "Nuovo run",
  history: "Storico",
  settings: "Impostazioni",
  upload: "Carica",
  processing: "Elaborazione",
  verify: "Verifica fornitori",
  review: "Verifica righe",
  creating: "Creazione",
  results: "Risultati",
};

function buildCrumbs(pathname: string) {
  const parts = pathname.split("/").filter(Boolean);
  const crumbs = [{ label: "Dashboard", to: "/" }];
  let acc = "";
  for (const p of parts) {
    acc += `/${p}`;
    crumbs.push({ label: ROUTE_LABELS[p] ?? p, to: acc });
  }
  return crumbs;
}

interface TopBarProps {
  companyName?: string;
}

export function TopBar({ companyName = "Mailift Srl" }: TopBarProps) {
  const { pathname } = useLocation();
  const crumbs = buildCrumbs(pathname);

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border bg-background/80 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      {/* Breadcrumb */}
      <nav
        aria-label="Breadcrumb"
        className="flex min-w-0 flex-1 items-center gap-1.5 text-sm"
      >
        {crumbs.map((c, i) => {
          const isLast = i === crumbs.length - 1;
          return (
            <div key={c.to} className="flex items-center gap-1.5">
              {i > 0 && (
                <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
              )}
              {isLast ? (
                <span className="truncate font-medium text-foreground">
                  {c.label}
                </span>
              ) : (
                <Link
                  to={c.to}
                  className="truncate text-muted-foreground transition-colors hover:text-foreground"
                >
                  {c.label}
                </Link>
              )}
            </div>
          );
        })}
      </nav>

      {/* Right cluster */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          className={cn(
            "hidden items-center gap-1.5 rounded-md border border-border/60 bg-muted/40 px-2 py-1 text-[11px] text-muted-foreground transition-colors hover:bg-muted md:inline-flex"
          )}
          aria-label="Apri command palette"
        >
          <CommandIcon className="h-3 w-3" />
          <span className="font-medium">K</span>
        </button>
        <Separator orientation="vertical" className="h-6" />
        <EnvironmentSwitch />
        <Separator orientation="vertical" className="h-6" />
        <Badge variant="outline" className="hidden sm:inline-flex">
          {companyName}
        </Badge>
      </div>
    </header>
  );
}
