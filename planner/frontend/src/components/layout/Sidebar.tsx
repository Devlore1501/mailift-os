import { NavLink } from "react-router-dom";
import {
  CalendarDays,
  Home,
  Mail,
  Package,
  Plug,
  Settings,
  SwatchBook,
  UserRound,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useBrand } from "@/lib/queries";

interface SidebarProps {
  brandId: number | null;
  className?: string;
}

function NavItem({
  to,
  label,
  icon: Icon,
  end,
}: {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  end?: boolean;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        cn(
          "group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors duration-200",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          isActive
            ? "bg-sidebar-accent text-sidebar-foreground"
            : "text-sidebar-muted hover:bg-sidebar-accent/60 hover:text-sidebar-foreground"
        )
      }
    >
      {({ isActive }) => (
        <>
          <span
            aria-hidden
            className={cn(
              "absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-amber-400 transition-opacity duration-200",
              isActive ? "opacity-100" : "opacity-0"
            )}
          />
          <Icon
            className={cn(
              "h-4 w-4 shrink-0 transition-colors",
              isActive ? "text-amber-400" : "text-sidebar-muted group-hover:text-sidebar-foreground"
            )}
          />
          <span className="truncate">{label}</span>
        </>
      )}
    </NavLink>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="px-3 pb-1.5 pt-5 text-[10px] font-semibold uppercase tracking-[0.14em] text-sidebar-muted/80">
      {children}
    </div>
  );
}

export function Sidebar({ brandId, className }: SidebarProps) {
  const { data: brand } = useBrand(brandId);

  return (
    <aside
      className={cn(
        "flex h-screen w-[248px] flex-col bg-sidebar text-sidebar-foreground",
        className
      )}
      aria-label="Navigazione principale"
    >
      {/* Brand mark */}
      <div className="flex h-16 items-center gap-2.5 px-4">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 via-violet-500 to-amber-400 shadow-lg shadow-indigo-950/40">
          <Mail className="h-4 w-4 text-white" />
        </div>
        <div className="flex min-w-0 flex-col leading-tight">
          <span className="truncate font-display text-[15px] font-semibold tracking-tight">
            Mailift Planner
          </span>
          <span className="truncate text-[10px] uppercase tracking-[0.18em] text-sidebar-muted">
            Email studio
          </span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-2">
        <SectionLabel>Agenzia</SectionLabel>
        <NavItem to="/" label="Dashboard" icon={Home} end />

        {brandId != null && (
          <>
            <SectionLabel>{brand?.name ?? "Brand"}</SectionLabel>
            <NavItem
              to={`/brands/${brandId}/plans`}
              label="Piani"
              icon={CalendarDays}
            />
            <NavItem
              to={`/brands/${brandId}/profile`}
              label="Profilo brand"
              icon={UserRound}
            />
            <NavItem
              to={`/brands/${brandId}/catalog`}
              label="Catalogo"
              icon={Package}
            />
            <NavItem
              to={`/brands/${brandId}/integrations`}
              label="Integrazioni"
              icon={Plug}
            />
          </>
        )}
      </nav>

      <div className="space-y-0.5 border-t border-sidebar-border px-3 py-3">
        <NavItem to="/templates" label="Template" icon={SwatchBook} />
        <NavItem to="/settings" label="Impostazioni" icon={Settings} />
      </div>
    </aside>
  );
}
