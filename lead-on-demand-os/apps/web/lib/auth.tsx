"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, getToken, setToken } from "./api";

export type Role = "SUPER_ADMIN" | "MANAGER" | "OPERATOR" | "CLIENT";
export interface AuthUser {
  id: string;
  email: string;
  fullName: string;
  role: Role;
  clientId: string | null;
}

interface AuthState {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<AuthUser>;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({ user: null, loading: true, login: async () => { throw new Error("no provider"); }, logout: () => {} });

export function homeFor(role: Role): string {
  switch (role) {
    case "CLIENT":
      return "/portal";
    case "OPERATOR":
      return "/operator";
    default:
      return "/admin";
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    api<{ user: AuthUser }>("/auth/me")
      .then((r) => setUser(r.user))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const r = await api<{ token: string; user: AuthUser }>("/auth/login", { method: "POST", json: { email, password } });
    setToken(r.token);
    setUser(r.user);
    return r.user;
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    window.location.href = "/login";
  }, []);

  const value = useMemo(() => ({ user, loading, login, logout }), [user, loading, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
