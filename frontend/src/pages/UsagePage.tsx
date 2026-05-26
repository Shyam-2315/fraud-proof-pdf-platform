import { useEffect, useState } from "react";
import { getAccountUsage, type AccountUsage } from "../api/authApi";
import { getVisitorStatusAfterIdentify, type VisitorStatus } from "../api/userApi";
import AccountUsageCard from "../components/AccountUsageCard";
import ErrorState from "../components/ErrorState";
import Footer from "../components/Footer";
import LoadingState from "../components/LoadingState";
import Navbar from "../components/Navbar";
import UsageCard from "../components/UsageCard";
import { useAuth } from "../context/AuthContext";

export default function UsagePage() {
  const [status, setStatus] = useState<VisitorStatus | null>(null);
  const [accountUsage, setAccountUsage] = useState<AccountUsage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    async function load() {
      try {
        if (isAuthenticated) {
          setAccountUsage(await getAccountUsage());
        } else {
          setStatus(await getVisitorStatusAfterIdentify());
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load usage.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [isAuthenticated]);

  return (
    <div>
      <Navbar />
      <main className="shell py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-black text-[#10213f]">Your usage</h1>
          <p className="mt-2 text-sm font-semibold text-[#52647f]">Track your free PDF generations.</p>
        </div>
        {loading ? <LoadingState label="Loading usage..." /> : null}
        {error ? <ErrorState message={error} /> : null}
        {!loading && !error && isAuthenticated && accountUsage ? (
          <div className="grid gap-6 lg:grid-cols-[420px_1fr]">
            <AccountUsageCard usage={accountUsage} />
            <section className="panel p-5">
              <h2 className="text-xl font-black text-[#10213f]">Plan access</h2>
              <p className="mt-2 text-sm font-semibold text-[#52647f]">
                Your plan includes {accountUsage.limit} PDFs each month.
              </p>
            </section>
          </div>
        ) : null}
        {!loading && !error && !isAuthenticated ? (
          <div className="grid gap-6 lg:grid-cols-[420px_1fr]">
            <UsageCard status={status} />
            <section className="panel p-5">
              <h2 className="text-xl font-black text-[#10213f]">Account access</h2>
              <p className="mt-2 text-sm font-semibold text-[#52647f]">
                Account required after free limit.
              </p>
              {status?.requires_login ? (
                <p className="mt-5 rounded-lg bg-[#fff4d8] p-4 text-sm font-black text-[#765000]">
                  You have used your free PDF generations. Please log in to continue.
                </p>
              ) : null}
            </section>
          </div>
        ) : null}
      </main>
      <Footer />
    </div>
  );
}
