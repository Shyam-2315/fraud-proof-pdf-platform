import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { getFraudVisitors, type AdminVisitor } from "../api/adminApi";
import AdminNavbar from "../components/AdminNavbar";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import VisitorTable from "../components/VisitorTable";

export default function AdminVisitorsPage() {
  const [visitors, setVisitors] = useState<AdminVisitor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    async function load() {
      try {
        setVisitors((await getFraudVisitors()).items);
      } catch (err) {
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          navigate("/admin/login", { replace: true, state: { message: err.status === 401 ? "Admin API key required" : "Invalid admin API key" } });
          return;
        }
        setError(err instanceof Error ? err.message : "Unable to load visitors.");
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
          <h1 className="text-3xl font-black text-[#10213f]">Visitors</h1>
          <p className="mt-2 text-sm font-semibold text-[#52647f]">Sorted by risk score and recent activity.</p>
        </div>
        {loading ? <LoadingState label="Loading visitors..." /> : null}
        {error ? <ErrorState message={error} /> : null}
        {!loading && !error ? <VisitorTable visitors={visitors} /> : null}
      </main>
    </div>
  );
}
