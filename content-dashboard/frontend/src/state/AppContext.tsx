// Stato globale: utente autenticato + config (enum, soglie, target) dal backend.
import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

import { api, getToken, setToken } from "@/lib/api";
import type { AppConfig, User } from "@/types";

interface AppState {
  user: User | null;
  config: AppConfig | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  reloadConfig: () => Promise<void>;
  isEditor: boolean; // editor o admin
  isAdmin: boolean;
}

const Ctx = createContext<AppState | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [loading, setLoading] = useState(true);

  const reloadConfig = useCallback(async () => {
    setConfig(await api.get<AppConfig>("/api/config"));
  }, []);

  useEffect(() => {
    const onLogout = () => setUser(null);
    window.addEventListener("mailift-logout", onLogout);
    return () => window.removeEventListener("mailift-logout", onLogout);
  }, []);

  useEffect(() => {
    (async () => {
      if (!getToken()) {
        setLoading(false);
        return;
      }
      try {
        const me = await api.get<User>("/api/auth/me");
        setUser(me);
        await reloadConfig();
      } catch {
        setToken(null);
      } finally {
        setLoading(false);
      }
    })();
  }, [reloadConfig]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.post<{ token: string; user: User }>("/api/auth/login", { email, password });
    setToken(res.token);
    setUser(res.user);
    await reloadConfig();
  }, [reloadConfig]);

  const logout = useCallback(() => {
    api.post("/api/auth/logout").catch(() => {});
    setToken(null);
    setUser(null);
  }, []);

  return (
    <Ctx.Provider
      value={{
        user,
        config,
        loading,
        login,
        logout,
        reloadConfig,
        isEditor: user?.role === "admin" || user?.role === "editor",
        isAdmin: user?.role === "admin",
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export function useApp(): AppState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useApp fuori da AppProvider");
  return ctx;
}
