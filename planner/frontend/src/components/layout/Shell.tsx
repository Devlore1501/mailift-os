import { useEffect } from "react";
import { Outlet, useMatch } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { getLastBrandId, setLastBrandId } from "@/lib/brand";

/**
 * Shell dell'app: sidebar fissa + topbar sticky + main scrollabile.
 * Il brand "attivo" viene dal param di route :brandId; se assente
 * (es. /templates) si usa l'ultimo brand salvato in localStorage.
 */
export function Shell() {
  const match = useMatch("/brands/:brandId/*");
  const routeBrandId = match?.params.brandId
    ? Number(match.params.brandId)
    : null;
  const brandId =
    routeBrandId && Number.isFinite(routeBrandId)
      ? routeBrandId
      : getLastBrandId();

  useEffect(() => {
    if (routeBrandId && Number.isFinite(routeBrandId)) {
      setLastBrandId(routeBrandId);
    }
  }, [routeBrandId]);

  return (
    <TooltipProvider delayDuration={150}>
      <div className="flex min-h-screen w-full bg-background text-foreground">
        <Sidebar brandId={brandId} />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar brandId={brandId} />
          <main className="flex-1 overflow-auto px-6 py-8 lg:px-10">
            <Outlet />
          </main>
        </div>
      </div>
    </TooltipProvider>
  );
}
