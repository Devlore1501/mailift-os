import { Routes, Route, Navigate } from "react-router-dom";
import { Shell } from "@/components/layout/Shell";
import { Dashboard } from "@/pages/Dashboard";
import { NewRunLayout } from "@/pages/NewRun";
import { Upload } from "@/pages/NewRun/Upload";
import { Processing } from "@/pages/NewRun/Processing";
import { VerifySuppliers } from "@/pages/NewRun/VerifySuppliers";
import { Review } from "@/pages/NewRun/Review";
import { Creating } from "@/pages/NewRun/Creating";
import { Results } from "@/pages/NewRun/Results";
import { History } from "@/pages/History";
import { HistoryDetail } from "@/pages/HistoryDetail";
import { Settings } from "@/pages/Settings";

export function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<Dashboard />} />
        <Route path="new" element={<NewRunLayout />}>
          <Route index element={<Upload />} />
          <Route
            path="processing/:statementId"
            element={<Processing />}
          />
          <Route
            path="verify/:statementId"
            element={<VerifySuppliers />}
          />
          <Route path="review/:statementId" element={<Review />} />
          <Route path="creating/:jobId" element={<Creating />} />
          <Route path="results/:jobId" element={<Results />} />
        </Route>
        <Route path="history" element={<History />} />
        <Route path="history/:id" element={<HistoryDetail />} />
        <Route path="settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
