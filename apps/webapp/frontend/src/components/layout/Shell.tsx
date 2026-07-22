import { Outlet } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { TooltipProvider } from "@/components/ui/tooltip";

/**
 * Top-level app shell: fixed sidebar + sticky top bar + scrollable main Outlet.
 * Wraps the app in TooltipProvider so any nested Tooltip just works.
 */
export function Shell() {
  return (
    <TooltipProvider delayDuration={150}>
      <div className="flex min-h-screen w-full bg-background text-foreground">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar />
          <main className="flex-1 overflow-auto px-6 py-6">
            <Outlet />
          </main>
        </div>
      </div>
    </TooltipProvider>
  );
}
