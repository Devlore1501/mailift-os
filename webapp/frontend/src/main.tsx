import { StrictMode } from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router";
import { Toaster } from "@/components/ui/sonner";
import { initTheme } from "@/lib/theme";
import { App } from "@/App";
import { AuthGate } from "@/components/layout/AuthGate";
import "@/index.css";

// Apply saved theme before first paint to avoid light-mode flash.
initTheme();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5_000,
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthGate>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </AuthGate>
      <Toaster richColors position="top-right" />
    </QueryClientProvider>
  </StrictMode>
);
