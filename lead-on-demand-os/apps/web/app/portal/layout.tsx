import { Shell } from "@/components/Shell";

const nav = [
  { href: "/portal", label: "Dashboard" },
  { href: "/portal/leads", label: "Lead" },
  { href: "/portal/appointments", label: "Appuntamenti" },
  { href: "/portal/package", label: "Pacchetto" },
  { href: "/portal/stats", label: "Statistiche" },
  { href: "/portal/support", label: "Supporto" },
];

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  return (
    <Shell nav={nav} roles={["CLIENT"]} title="Portale cliente">
      {children}
    </Shell>
  );
}
