"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ErrorBox, Field, PageTitle } from "@/components/ui";
import { api } from "@/lib/api";

export default function NewLeadPage() {
  const router = useRouter();
  const [form, setForm] = useState({ firstName: "", lastName: "", phone: "", email: "", address: "", municipality: "", postalCode: "", province: "", region: "", leadType: "RESIDENTIAL", source: "manual", campaignName: "", consentRecorded: true });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: string, v: string | boolean) => setForm({ ...form, [k]: v });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const lead = await api<{ id: string }>("/leads", { method: "POST", json: { ...form, sourceName: "Inserimento manuale" } });
      router.push(`/admin/leads/${lead.id}`);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <PageTitle title="Nuovo lead manuale" subtitle="Per lead arrivati da canali non integrati. Il controllo duplicati si applica comunque." />
      <ErrorBox error={error} />
      <form onSubmit={submit} className="card grid grid-cols-1 gap-3 md:grid-cols-2">
        <Field label="Nome"><input className="input" value={form.firstName} onChange={(e) => set("firstName", e.target.value)} /></Field>
        <Field label="Cognome"><input className="input" value={form.lastName} onChange={(e) => set("lastName", e.target.value)} /></Field>
        <Field label="Telefono"><input className="input" value={form.phone} onChange={(e) => set("phone", e.target.value)} required /></Field>
        <Field label="Email"><input className="input" type="email" value={form.email} onChange={(e) => set("email", e.target.value)} /></Field>
        <Field label="Indirizzo"><input className="input" value={form.address} onChange={(e) => set("address", e.target.value)} /></Field>
        <Field label="Comune"><input className="input" value={form.municipality} onChange={(e) => set("municipality", e.target.value)} /></Field>
        <Field label="CAP"><input className="input" value={form.postalCode} onChange={(e) => set("postalCode", e.target.value)} /></Field>
        <Field label="Provincia (sigla)"><input className="input" value={form.province} onChange={(e) => set("province", e.target.value.toUpperCase())} maxLength={2} required /></Field>
        <Field label="Regione"><input className="input" value={form.region} onChange={(e) => set("region", e.target.value)} /></Field>
        <Field label="Tipologia">
          <select className="input" value={form.leadType} onChange={(e) => set("leadType", e.target.value)}>
            <option value="RESIDENTIAL">Residenziale</option>
            <option value="BUSINESS">Aziendale</option>
          </select>
        </Field>
        <Field label="Fonte"><input className="input" value={form.source} onChange={(e) => set("source", e.target.value)} /></Field>
        <Field label="Campagna"><input className="input" value={form.campaignName} onChange={(e) => set("campaignName", e.target.value)} /></Field>
        <label className="flex items-center gap-2 text-sm md:col-span-2"><input type="checkbox" checked={form.consentRecorded} onChange={(e) => set("consentRecorded", e.target.checked)} /> Consenso al trattamento registrato</label>
        <div className="md:col-span-2"><button className="btn-primary" disabled={busy}>Crea lead</button></div>
      </form>
    </div>
  );
}
