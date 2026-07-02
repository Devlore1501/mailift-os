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
import { Separator } from "@/components/ui/separator";
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
          "flex items-center gap-3 rounded-md px-2 py-2 text-sm font-medium transition-colors",
          "hover:bg-accent hover:text-accent-foreground",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          isActive ? "bg-accent text-accent-foreground" : "text-muted-foreground"
        )
      }
    >
      <Icon className="h-4 w-4 shrink-0" />
      <span className="truncate">{label}</span>
    </NavLink>
  );
}

export function Sidebar({ brandId, className }: SidebarProps) {
  const { data: brand } = useBrand(brandId);

  return (
    <aside
      className={cn(
        "flex h-screen w-[240px] flex-col border-r border-border bg-card/50",
        className
      )}
      aria-label="Navigazione principale"
    >
      {/* Logo */}
      <div className="flex h-14 items-center gap-2 px-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <Mail className="h-4 w-4" />
        </div>
        <div className="flex min-w-0 flex-col leading-tight">
          <span className="truncate text-sm font-semibold">
            Mailift Planner
          </span>
          <span className="truncate text-[10px] uppercase tracking-wide text-muted-foreground">
            Email marketing
          </span>
        </div>
      </div>
      <Separator />

      {/* Nav */}
      <nav className="flex-1 space-y-0.5 px-2 py-3">
        <NavItem to="/" label="Dashboard" icon={Home} end />

        {brandId != null && (
          <>
            <div className="px-2 pb-1 pt-4 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              {brand?.name ?? "Brand"}
            </div>
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

      <Separator />
      <div className="space-y-0.5 px-2 py-3">
        <NavItem to="/templates" label="Template" icon={SwatchBook} />
        <NavItem to="/settings" label="Impostazioni" icon={Settings} />
      </div>
    </aside>
  );
}
