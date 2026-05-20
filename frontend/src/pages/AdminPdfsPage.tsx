import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { getAllPdfs, type AdminPdf } from "../api/adminApi";
import AdminNavbar from "../components/AdminNavbar";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";

export default function AdminPdfsPage() {
  const [pdfs, setPdfs] = useState<AdminPdf[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    async function load() {
      try {
        setPdfs((await getAllPdfs()).items);
      } catch (err) {
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          navigate("/admin/login", { replace: true, state: { message: err.status === 401 ? "Admin API key required" : "Invalid admin API key" } });
          return;
        }
        setError(err instanceof Error ? err.message : "Unable to load PDFs.");
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
          <h1 className="text-3xl font-black text-[#10213f]">All Generated PDFs</h1>
          <p className="mt-2 text-sm font-semibold text-[#52647f]">Internal document generation log.</p>
        </div>
        {loading ? <LoadingState label="Loading PDFs..." /> : null}
        {error ? <ErrorState message={error} /> : null}
        {!loading && !error ? (
          <div className="panel table-wrap">
            <table>
              <thead>
                <tr>
                  <th>PDF ID</th>
                  <th>Visitor ID</th>
                  <th>Title</th>
                  <th>File name</th>
                  <th>Created</th>
                  <th>Fingerprint hash</th>
                  <th>IP address</th>
                </tr>
              </thead>
              <tbody>
                {pdfs.map((pdf) => (
                  <tr key={pdf.pdf_id}>
                    <td className="font-mono text-xs">{pdf.pdf_id}</td>
                    <td className="font-mono text-xs">{pdf.visitor_id || "-"}</td>
                    <td>{pdf.title}</td>
                    <td>{pdf.file_name}</td>
                    <td>{new Date(pdf.created_at).toLocaleString()}</td>
                    <td className="font-mono text-xs">{pdf.fingerprint_hash || "-"}</td>
                    <td>{pdf.ip_address || "-"}</td>
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
