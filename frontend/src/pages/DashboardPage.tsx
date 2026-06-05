import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CreditCard, FileText, History, TrendingUp } from "lucide-react";
import { getAccountUsage, type AccountUsage } from "../api/authApi";
import { getMyPdfHistory, type PdfHistory } from "../api/userApi";
import AccountUsageCard from "../components/AccountUsageCard";
import ErrorState from "../components/ErrorState";
import Footer from "../components/Footer";
import LoadingState from "../components/LoadingState";
import Navbar from "../components/Navbar";
import PdfHistoryTable from "../components/PdfHistoryTable";
import { useAuth } from "../context/AuthContext";

export default function DashboardPage() {
  const { user } = useAuth();
  const [usage, setUsage] = useState<AccountUsage | null>(null);
  const [history, setHistory] = useState<PdfHistory | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [usageResponse, historyResponse] = await Promise.all([
          getAccountUsage(),
          getMyPdfHistory(),
        ]);
        setUsage(usageResponse);
        setHistory(historyResponse);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load dashboard.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div>
      <Navbar />
      <main className="shell py-8">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-black text-[#10213f]">Dashboard</h1>
            <p className="mt-2 text-sm font-semibold text-[#52647f]">{user?.email}</p>
          </div>
          <Link className="btn-primary" to="/pricing">
            <TrendingUp size={17} />
            Upgrade
          </Link>
        </div>

        {loading ? <LoadingState label="Loading dashboard..." /> : null}
        {error ? <ErrorState message={error} /> : null}

        {!loading && !error && usage ? (
          <div className="space-y-6">
            <section className="grid gap-4 sm:grid-cols-3">
              <MetricCard icon={CreditCard} label="Current plan" value={usage.plan} />
              <MetricCard icon={FileText} label="PDFs generated" value={String(usage.used)} />
              <MetricCard icon={History} label="Remaining usage" value={String(usage.remaining)} />
            </section>

            <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
              <div className="space-y-4">
                <AccountUsageCard usage={usage} />
                <section className="panel p-5">
                  <h2 className="text-xl font-black text-[#10213f]">Plan access</h2>
                  <p className="mt-2 text-sm font-semibold text-[#52647f]">
                    {usage.requires_upgrade
                      ? "Upgrade to keep generating PDFs this month."
                      : "Upgrade options are available when you need more volume."}
                  </p>
                  <Link className="btn-primary mt-4" to="/pricing">View plans</Link>
                </section>
              </div>
              <section>
                <div className="mb-3 flex items-center justify-between gap-3">
                  <h2 className="text-xl font-black text-[#10213f]">Recent PDFs</h2>
                  <Link className="text-sm font-black text-[#1459d9]" to="/history">View all</Link>
                </div>
                <PdfHistoryTable items={(history?.items || []).slice(0, 5)} />
              </section>
            </div>
          </div>
        ) : null}
      </main>
      <Footer />
    </div>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof CreditCard;
  label: string;
  value: string;
}) {
  return (
    <section className="panel p-5">
      <div className="mb-3 flex items-center gap-3">
        <div className="rounded-lg bg-[#eaf1ff] p-2 text-[#1459d9]">
          <Icon size={20} />
        </div>
        <div className="text-sm font-bold text-[#52647f]">{label}</div>
      </div>
      <div className="text-2xl font-black text-[#10213f]">{value}</div>
    </section>
  );
}
