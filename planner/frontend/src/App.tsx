import { Routes, Route, Navigate } from "react-router-dom";
import { Shell } from "@/components/layout/Shell";
import { Dashboard } from "@/pages/Dashboard";
import { Plans } from "@/pages/Plans";
import { PlanDetail } from "@/pages/PlanDetail";
import { BrandProfile } from "@/pages/BrandProfile";
import { Catalog } from "@/pages/Catalog";
import { Integrations } from "@/pages/Integrations";
import { Templates } from "@/pages/Templates";
import { Settings } from "@/pages/Settings";

export function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<Dashboard />} />
        <Route path="brands/:brandId/plans" element={<Plans />} />
        <Route path="brands/:brandId/plans/:planId" element={<PlanDetail />} />
        <Route path="brands/:brandId/profile" element={<BrandProfile />} />
        <Route path="brands/:brandId/catalog" element={<Catalog />} />
        <Route path="brands/:brandId/integrations" element={<Integrations />} />
        <Route path="templates" element={<Templates />} />
        <Route path="settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
