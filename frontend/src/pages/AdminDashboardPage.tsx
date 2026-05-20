import { Activity, AlertTriangle, BarChart3, Bot, Brain, Database, FileCheck2, FileX2, Link2, Network, ShieldAlert, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { getFraudSummary, type FraudSummary } from "../api/adminApi";
import AdminNavbar from "../components/AdminNavbar";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import StatCard from "../components/StatCard";

function useAdminRedirect() {
  const navigate = useNavigate();
  return (err: unknown) => {
    if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
      navigate("/admin/login", {
        replace: true,
        state: { message: err.status === 401 ? "Admin API key required" : "Invalid admin API key" },
      });
      return true;
    }
    return false;
  };
}

export default function AdminDashboardPage() {
  const [summary, setSummary] = useState<FraudSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const handleAdminError = useAdminRedirect();

  useEffect(() => {
    async function load() {
      try {
        setSummary(await getFraudSummary());
      } catch (err) {
        if (!handleAdminError(err)) setError(err instanceof Error ? err.message : "Unable to load dashboard.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div>
      <AdminNavbar />
      <main className="shell py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-black text-[#10213f]">Internal Fraud Monitoring</h1>
          <p className="mt-2 text-sm font-semibold text-[#52647f]">
            Monitor free-limit abuse, blocked attempts, and visitor behavior.
          </p>
        </div>
        {loading ? <LoadingState label="Loading dashboard..." /> : null}
        {error ? <ErrorState message={error} /> : null}
        {summary ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <StatCard label="Total Visitors" value={summary.total_visitors} icon={Users} />
            <StatCard label="Blocked Visitors" value={summary.blocked_visitors} icon={ShieldAlert} />
            <StatCard label="Generated PDFs" value={summary.total_generated_pdfs} icon={BarChart3} />
            <StatCard label="Fraud Events" value={summary.total_fraud_events} icon={Activity} />
            <StatCard label="Allowed Generations" value={summary.allowed_pdf_generations} icon={FileCheck2} />
            <StatCard label="Blocked Generations" value={summary.blocked_pdf_generations} icon={FileX2} />
            <StatCard label="Critical Risk Visitors" value={summary.critical_risk_visitors} icon={ShieldAlert} />
            <StatCard label="High Risk Visitors" value={summary.high_risk_visitors} icon={AlertTriangle} />
            <StatCard label="Medium Risk Visitors" value={summary.medium_risk_visitors} icon={AlertTriangle} />
            <StatCard label="Low Risk Visitors" value={summary.low_risk_visitors} icon={AlertTriangle} />
            <StatCard label="VPN/proxy Attempts" value={summary.vpn_proxy_attempts} icon={Network} />
            <StatCard label="Automation Signals" value={summary.automation_signals} icon={Bot} />
            <StatCard label="Linked Duplicate Visitors" value={summary.linked_duplicate_visitors} icon={Link2} />
            <StatCard label="Account Farming Signals" value={summary.account_farming_signals} icon={Users} />
            <StatCard label="ML Decisions Today" value={summary.ml_decisions_today} icon={Brain} />
            <StatCard label="Identity Links Created" value={summary.identity_links_created} icon={Link2} />
            <StatCard label="Training Events Collected" value={summary.training_events_collected} icon={Database} />
          </div>
        ) : null}
      </main>
    </div>
  );
}
