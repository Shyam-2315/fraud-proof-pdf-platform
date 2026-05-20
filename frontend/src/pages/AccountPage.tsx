import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getAccountUsage, type AccountUsage } from "../api/authApi";
import AccountUsageCard from "../components/AccountUsageCard";
import ErrorState from "../components/ErrorState";
import Footer from "../components/Footer";
import LoadingState from "../components/LoadingState";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";

export default function AccountPage() {
  const { user, logout } = useAuth();
  const [usage, setUsage] = useState<AccountUsage | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        setUsage(await getAccountUsage());
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load account usage.");
      }
    }
    load();
  }, []);

  return (
    <div>
      <Navbar />
      <main className="shell py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-black text-[#10213f]">Account</h1>
          <p className="mt-2 text-sm font-semibold text-[#52647f]">Manage your PDFCraft plan and monthly usage.</p>
        </div>
        <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
          <section className="panel p-5">
            <h2 className="text-xl font-black text-[#10213f]">{user?.full_name || "PDFCraft user"}</h2>
            <p className="mt-2 text-sm font-semibold text-[#52647f]">{user?.email}</p>
            <div className="mt-5 inline-flex rounded-full bg-[#eaf1ff] px-3 py-1 text-sm font-black text-[#1459d9]">
              {user?.plan || "FREE"} plan
            </div>
            <div className="mt-6 grid gap-3">
              <Link className="btn-primary w-full" to="/pricing">View plans</Link>
              <button className="btn-secondary w-full" type="button" onClick={() => void logout()}>Logout</button>
            </div>
          </section>
          <div>
            {error ? <ErrorState message={error} /> : null}
            {!error && !usage ? <LoadingState label="Loading account usage..." /> : null}
            {usage ? <AccountUsageCard usage={usage} /> : null}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
