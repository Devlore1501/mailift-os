import { useEffect, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { AUTH_EXPIRED_EVENT } from "@/lib/api";
import { useAuth } from "@/lib/queries";
import { Login } from "@/pages/Login";

/** Mostra il login finche' il backend non riconosce la sessione. */
export function AuthGate({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const { data, isLoading } = useAuth();

  useEffect(() => {
    const onExpired = () =>
      qc.setQueryData(["auth"], { authenticated: false, auth_enabled: true });
    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired);
  }, [qc]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (!data?.authenticated) return <Login />;
  return <>{children}</>;
}
