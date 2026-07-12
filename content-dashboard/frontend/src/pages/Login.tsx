import { FormEvent, useState } from "react";

import { ErrorBox } from "@/components/ui";
import { useApp } from "@/state/AppContext";

export default function Login() {
  const { login } = useApp();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
    } catch (err) {
      setError((err as Error).message || "Login fallito");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="card w-full max-w-sm p-8">
        <div className="mb-8 text-center">
          <div className="font-extrabold text-2xl tracking-tight">
            Mailift<span className="text-gold-500">.</span>
          </div>
          <div className="text-xs uppercase tracking-widest text-ink-500 font-semibold mt-1">
            Content Dashboard
          </div>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="label" htmlFor="login-email">Email</label>
            <input
              id="login-email" className="input" type="email" autoComplete="email"
              value={email} onChange={(e) => setEmail(e.target.value)} required
            />
          </div>
          <div>
            <label className="label" htmlFor="login-password">Password</label>
            <input
              id="login-password" className="input" type="password" autoComplete="current-password"
              value={password} onChange={(e) => setPassword(e.target.value)} required
            />
          </div>
          {error && <ErrorBox message={error} />}
          <button type="submit" className="btn-gold w-full justify-center" disabled={busy}>
            {busy ? "Accesso…" : "Entra"}
          </button>
        </form>
      </div>
    </div>
  );
}
