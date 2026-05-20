import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { getAuditLogs, type AuditLog } from "../api/adminApi";
import AdminNavbar from "../components/AdminNavbar";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";

export default function AdminAuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    async function load() {
      try {
        setLogs((await getAuditLogs()).items);
      } catch (err) {
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          navigate("/admin/login", { replace: true, state: { message: err.status === 401 ? "Admin API key required" : "Invalid admin API key" } });
          return;
        }
        setError(err instanceof Error ? err.message : "Unable to load audit logs.");
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
          <h1 className="text-3xl font-black text-[#10213f]">Admin Audit Logs</h1>
          <p className="mt-2 text-sm font-semibold text-[#52647f]">Successful admin endpoint access history.</p>
        </div>
        {loading ? <LoadingState label="Loading audit logs..." /> : null}
        {error ? <ErrorState message={error} /> : null}
        {!loading && !error ? (
          <div className="panel table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Created</th>
                  <th>Action</th>
                  <th>Target type</th>
                  <th>Target ID</th>
                  <th>Metadata</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id}>
                    <td>{new Date(log.created_at).toLocaleString()}</td>
                    <td>{log.action}</td>
                    <td>{log.target_type}</td>
                    <td className="font-mono text-xs">{log.target_id || "-"}</td>
                    <td>
                      <pre className="max-w-lg overflow-auto text-xs">{JSON.stringify(log.metadata)}</pre>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </main>
    </div>
  );
}
