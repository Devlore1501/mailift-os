"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth, type Role } from "@/lib/auth";

export interface NavItem {
  href: string;
  label: string;
}

export function Shell({ nav, roles, title, children }: { nav: NavItem[]; roles: Role[]; title: string; children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!user) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    else if (!roles.includes(user.role)) router.replace("/");
  }, [user, loading, roles, router, pathname]);

  if (loading || !user || !roles.includes(user.role)) return <div className="p-8 text-sm text-slate-500">Caricamento…</div>;

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-56 shrink-0 flex-col border-r border-slate-200 bg-white md:flex">
        <div className="border-b border-slate-200 px-4 py-4">
          <div className="text-sm font-semibold">Lead on Demand OS</div>
          <div className="text-xs text-slate-500">{title}</div>
        </div>
        <nav className="flex-1 space-y-0.5 p-2">
          {nav.map((n) => {
            const active = pathname === n.href || (n.href !== "/admin" && n.href !== "/portal" && n.href !== "/operator" && pathname.startsWith(n.href));
            return (
              <Link key={n.href} href={n.href} className={`block rounded-md px-3 py-2 text-sm ${active ? "bg-brand-50 font-medium text-brand-700" : "text-slate-700 hover:bg-slate-100"}`}>
                {n.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-slate-200 p-3 text-xs text-slate-600">
          <div className="truncate font-medium text-slate-800">{user.fullName}</div>
          <div className="truncate">{user.email}</div>
          <button onClick={logout} className="mt-2 text-brand-600 hover:underline">Esci</button>
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-2 md:hidden">
          <span className="text-sm font-semibold">Lead on Demand OS</span>
          <details className="relative">
            <summary className="cursor-pointer text-sm text-brand-600">Menu</summary>
            <div className="absolute right-0 z-10 mt-2 w-48 rounded-md border border-slate-200 bg-white p-2 shadow">
              {nav.map((n) => (
                <Link key={n.href} href={n.href} className="block rounded px-2 py-1 text-sm hover:bg-slate-100">{n.label}</Link>
              ))}
              <button onClick={logout} className="mt-1 block w-full rounded px-2 py-1 text-left text-sm text-red-600 hover:bg-slate-100">Esci</button>
            </div>
          </details>
        </header>
        <main className="min-w-0 flex-1 p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
