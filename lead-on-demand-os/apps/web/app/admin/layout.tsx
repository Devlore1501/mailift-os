import { Shell } from "@/components/Shell";

const nav = [
  { href: "/admin", label: "Dashboard" },
  { href: "/admin/leads", label: "Lead" },
  { href: "/admin/clients", label: "Clienti" },
  { href: "/admin/packages", label: "Pacchetti" },
  { href: "/admin/routing", label: "Routing" },
  { href: "/admin/territories", label: "Territori" },
  { href: "/admin/appointments", label: "Appuntamenti" },
  { href: "/admin/replacements", label: "Replacement" },
  { href: "/admin/campaigns", label: "Campagne" },
  { href: "/admin/analytics", label: "Analytics" },
  { href: "/admin/team", label: "Team" },
  { href: "/admin/integrations", label: "Integrazioni" },
  { href: "/admin/settings", label: "Impostazioni" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <Shell nav={nav} roles={["SUPER_ADMIN", "MANAGER"]} title="Amministrazione">
      {children}
    </Shell>
  );
}
