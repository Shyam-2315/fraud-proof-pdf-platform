import { Navigate, Route, Routes } from "react-router-dom";
import AccountPage from "./pages/AccountPage";
import GeneratePage from "./pages/GeneratePage";
import HistoryPage from "./pages/HistoryPage";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import PricingPage from "./pages/PricingPage";
import ProtectedRoute from "./components/ProtectedRoute";
import SignupPage from "./pages/SignupPage";
import UsagePage from "./pages/UsagePage";
import VerifyEmailPage from "./pages/VerifyEmailPage";

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
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/account" element={<AccountPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
