// Layout: sidebar di navigazione + area contenuto.
import {
  BarChart3,
  CalendarDays,
  KanbanSquare,
  LayoutDashboard,
  Lightbulb,
  LogOut,
  Settings,
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { useApp } from "@/state/AppContext";

const NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/piano", label: "Piano", icon: KanbanSquare },
  { to: "/calendario", label: "Calendario", icon: CalendarDays },
  { to: "/idee", label: "Idee", icon: Lightbulb },
  { to: "/performance", label: "Performance", icon: BarChart3 },
  { to: "/impostazioni", label: "Impostazioni", icon: Settings },
];

const ROLE_LABELS: Record<string, string> = {
  admin: "Admin",
  editor: "Editor",
  contributor: "Contributor",
};

export default function Shell() {
  const { user, logout } = useApp();

  return (
    <div className="min-h-screen flex">
      <aside className="w-56 shrink-0 border-r border-navy-700 bg-navy-900 flex flex-col sticky top-0 h-screen">
        <div className="px-5 py-5 border-b border-navy-700">
          <div className="font-extrabold text-lg tracking-tight">
            Mailift<span className="text-gold-500">.</span>
          </div>
          <div className="text-[11px] uppercase tracking-widest text-ink-500 font-semibold mt-0.5">
            Content Dashboard
          </div>
        </div>
        <nav className="flex-1 p-3 space-y-1" aria-label="Navigazione principale">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-semibold transition-colors duration-200 ${
                  isActive
                    ? "bg-gold-500/10 text-gold-400 border border-gold-500/25"
                    : "text-ink-300 hover:bg-navy-700/60 hover:text-ink-100 border border-transparent"
                }`
              }
            >
              <Icon className="w-4 h-4" aria-hidden />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-navy-700">
          <div className="px-3 py-2">
            <div className="text-sm font-semibold truncate">{user?.name}</div>
            <div className="text-xs text-ink-500">{ROLE_LABELS[user?.role ?? ""] ?? user?.role}</div>
          </div>
          <button className="btn-ghost w-full justify-center" onClick={logout}>
            <LogOut className="w-4 h-4" aria-hidden /> Esci
          </button>
        </div>
      </aside>
      <main className="flex-1 min-w-0 p-6 lg:p-8 max-w-[1600px]">
        <Outlet />
      </main>
    </div>
  );
}
