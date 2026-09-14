import { Shell } from "@/components/Shell";

const nav = [
  { href: "/operator", label: "Coda chiamate" },
  { href: "/operator/appointments", label: "Appuntamenti" },
];

export default function OperatorLayout({ children }: { children: React.ReactNode }) {
  return (
    <Shell nav={nav} roles={["OPERATOR", "MANAGER", "SUPER_ADMIN"]} title="Operatore">
      {children}
    </Shell>
  );
}
