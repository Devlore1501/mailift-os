import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import Shell from "@/components/Shell";
import { Spinner } from "@/components/ui";
import Board from "@/pages/Board";
import Calendar from "@/pages/Calendar";
import Ideas from "@/pages/Ideas";
import Login from "@/pages/Login";
import Overview from "@/pages/Overview";
import Performance from "@/pages/Performance";
import Settings from "@/pages/Settings";
import { useApp } from "@/state/AppContext";

export default function App() {
  const { user, loading } = useApp();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spinner label="Avvio…" />
      </div>
    );
  }

  if (!user) return <Login />;

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Shell />}>
          <Route index element={<Overview />} />
          <Route path="/piano" element={<Board />} />
          <Route path="/calendario" element={<Calendar />} />
          <Route path="/idee" element={<Ideas />} />
          <Route path="/performance" element={<Performance />} />
          <Route path="/impostazioni" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
