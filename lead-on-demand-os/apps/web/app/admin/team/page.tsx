"use client";

import { useState } from "react";
import { Badge, ErrorBox, Field, Modal, PageTitle, useApi } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmtDate } from "@/lib/format";
import { ROLE_LABELS } from "@/lib/labels";

interface Member { id: string; email: string; fullName: string; role: string; active: boolean; lastLoginAt: string | null }

export default function TeamPage() {
  const { user } = useAuth();
  const { data, error, reload } = useApi<Member[]>("/team");
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ fullName: "", email: "", password: "", role: "OPERATOR" });
  const [err, setErr] = useState<string | null>(null);
  const isSuper = user?.role === "SUPER_ADMIN";
  async function run(fn: () => Promise<unknown>) {
    setErr(null);
    try {
      await fn();
      setOpen(false);
      reload();
    } catch (e) {
      setErr((e as Error).message);
    }
  }
  return (
    <div>
      <PageTitle title="Team" subtitle="Utenti interni: super admin, manager e operatori" actions={isSuper && <button className="btn-primary" onClick={() => setOpen(true)}>Nuovo utente</button>} />
      <ErrorBox error={error ?? err} />
      {data && (
        <div className="card p-0">
          <table className="table">
            <thead><tr><th>Nome</th><th>Email</th><th>Ruolo</th><th>Ultimo accesso</th><th>Stato</th><th></th></tr></thead>
            <tbody>
              {data.map((m) => (
                <tr key={m.id}>
                  <td>{m.fullName}</td><td>{m.email}</td><td><Badge>{ROLE_LABELS[m.role]}</Badge></td><td>{fmtDate(m.lastLoginAt) || "mai"}</td><td>{m.active ? "attivo" : "disattivo"}</td>
                  <td>{isSuper && m.id !== user?.id && <button className="text-xs text-brand-600 hover:underline" onClick={() => run(() => api(`/team/${m.id}`, { method: "PATCH", json: { active: !m.active } }))}>{m.active ? "Disattiva" : "Riattiva"}</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Modal open={open} onClose={() => setOpen(false)} title="Nuovo utente interno">
        <div className="space-y-3">
          <Field label="Nome"><input className="input" value={f.fullName} onChange={(e) => setF({ ...f, fullName: e.target.value })} /></Field>
          <Field label="Email"><input className="input" type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
          <Field label="Password iniziale"><input className="input" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></Field>
          <Field label="Ruolo"><select className="input" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}><option value="OPERATOR">Operatore</option><option value="MANAGER">Manager</option><option value="SUPER_ADMIN">Super Admin</option></select></Field>
          <button className="btn-primary" disabled={!f.email || f.password.length < 8 || !f.fullName} onClick={() => run(() => api("/team", { method: "POST", json: f }))}>Crea</button>
        </div>
      </Modal>
    </div>
  );
}
