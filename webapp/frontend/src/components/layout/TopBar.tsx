import { useLocation, Link } from "react-router";
import { ChevronRight, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { MobileNav } from "@/components/layout/Sidebar";
import { useAuth, useLogout } from "@/lib/queries";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { EnvironmentSwitch } from "@/components/domain/EnvironmentSwitch";

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
  sdi: "Invio SDI",
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
  const { data: auth } = useAuth();
  const logout = useLogout();

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border bg-background/80 px-4 backdrop-blur-sm supports-backdrop-filter:bg-background/60">
      <MobileNav />
      {/* Breadcrumb */}
      <nav
        aria-label="Breadcrumb"
        className="flex min-w-0 flex-1 items-center gap-1.5 text-sm"
      >
        {crumbs.map((c, i) => {
          const isLast = i === crumbs.length - 1;
          return (
            <div
              key={c.to}
              className={isLast ? "flex min-w-0 items-center gap-1.5" : "hidden shrink-0 items-center gap-1.5 sm:flex"}
            >
              {i > 0 && (
                <ChevronRight className="hidden h-3.5 w-3.5 shrink-0 text-muted-foreground sm:block" />
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
      <div className="flex shrink-0 items-center gap-2 sm:gap-3">
        <EnvironmentSwitch />
        <Separator orientation="vertical" className="h-6" />
        <Badge variant="outline" className="hidden sm:inline-flex">
          {companyName}
        </Badge>
        {auth?.auth_enabled && (
          <Button
            variant="ghost"
            size="icon"
            aria-label="Esci"
            title="Esci"
            onClick={() => logout.mutate()}
          >
            <LogOut className="h-4 w-4" />
          </Button>
        )}
      </div>
    </header>
  );
}
