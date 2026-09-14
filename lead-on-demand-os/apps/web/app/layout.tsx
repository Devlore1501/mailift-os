import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";

export const metadata: Metadata = {
  title: "Lead on Demand OS",
  description: "Gestione Pay per Lead: pacchetti, routing, consegna, sostituzioni",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="it">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
