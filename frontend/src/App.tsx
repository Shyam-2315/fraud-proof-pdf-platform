import { Navigate, Route, Routes } from "react-router-dom";
import AdminAuditLogsPage from "./pages/AdminAuditLogsPage";
import AdminDashboardPage from "./pages/AdminDashboardPage";
import AdminEventsPage from "./pages/AdminEventsPage";
import AdminLoginPage from "./pages/AdminLoginPage";
import AdminMLEnginePage from "./pages/AdminMLEnginePage";
import AdminMLModelsPage from "./pages/AdminMLModelsPage";
import AdminPdfsPage from "./pages/AdminPdfsPage";
import AdminProtectedRoute from "./components/AdminProtectedRoute";
import AdminVisitorInvestigationPage from "./pages/AdminVisitorInvestigationPage";
import AdminVisitorsPage from "./pages/AdminVisitorsPage";
import AccountPage from "./pages/AccountPage";
import GeneratePage from "./pages/GeneratePage";
import HistoryPage from "./pages/HistoryPage";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import PricingPage from "./pages/PricingPage";
import ProtectedRoute from "./components/ProtectedRoute";
import SignupPage from "./pages/SignupPage";
import UsagePage from "./pages/UsagePage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/generate" element={<GeneratePage />} />
      <Route path="/usage" element={<UsagePage />} />
      <Route path="/history" element={<HistoryPage />} />
      <Route path="/pricing" element={<PricingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/account" element={<AccountPage />} />
      </Route>
      <Route path="/admin/login" element={<AdminLoginPage />} />
      <Route element={<AdminProtectedRoute />}>
        <Route path="/admin/dashboard" element={<AdminDashboardPage />} />
        <Route path="/admin/events" element={<AdminEventsPage />} />
        <Route path="/admin/ml" element={<AdminMLEnginePage />} />
        <Route path="/admin/ml/models" element={<AdminMLModelsPage />} />
        <Route path="/admin/visitors" element={<AdminVisitorsPage />} />
        <Route
          path="/admin/visitor/:visitorId"
          element={<AdminVisitorInvestigationPage />}
        />
        <Route path="/admin/pdfs" element={<AdminPdfsPage />} />
        <Route path="/admin/audit-logs" element={<AdminAuditLogsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
