"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ClientForm, emptyClient, toPayload } from "@/components/ClientForm";
import { ErrorBox, PageTitle } from "@/components/ui";
import { api } from "@/lib/api";

export default function NewClientPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  return (
    <div className="max-w-4xl">
      <PageTitle title="Nuovo cliente" />
      <ErrorBox error={error} />
      <ClientForm initial={emptyClient} busy={busy} submitLabel="Crea cliente" onSubmit={async (v) => {
        setBusy(true);
        setError(null);
        try {
          const c = await api<{ id: string }>("/clients", { method: "POST", json: toPayload(v) });
          router.push(`/admin/clients/${c.id}`);
        } catch (e) {
          setError((e as Error).message);
          setBusy(false);
        }
      }} />
    </div>
  );
}
