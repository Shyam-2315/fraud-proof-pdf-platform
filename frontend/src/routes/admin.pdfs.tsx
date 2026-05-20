import { createFileRoute, useRouter } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { getAllPdfs, items } from "@/api/adminApi";
import { useAdminGuard, handleAdminApiError } from "@/components/AdminProtectedRoute";
import { Card } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { formatDate, shortId } from "@/api/client";

export const Route = createFileRoute("/admin/pdfs")({ component: PdfsPage });

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type P = any;

function PdfsPage() {
  useAdminGuard();
  const router = useRouter();
  const [rows, setRows] = useState<P[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try { setRows(items<P>(await getAllPdfs())); }
      catch (e) { setError(handleAdminApiError(e, router)); }
      finally { setLoading(false); }
    })();
  }, [router]);

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">All PDFs</h1>
        <p className="text-sm text-slate-500">Every PDF generated across all visitors.</p>
      </div>
      {error && <Alert className="border-red-200 bg-red-50 text-red-800"><AlertDescription>{error}</AlertDescription></Alert>}
      <Card className="p-6 bg-white border-slate-200 shadow-sm">
        {loading ? <p className="text-slate-500">Loading…</p> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="py-2 pr-3 font-medium">PDF</th>
                  <th className="py-2 pr-3 font-medium">Visitor</th>
                  <th className="py-2 pr-3 font-medium">Title</th>
                  <th className="py-2 pr-3 font-medium">File</th>
                  <th className="py-2 pr-3 font-medium">Created</th>
                  <th className="py-2 pr-3 font-medium">Fingerprint</th>
                  <th className="py-2 font-medium">IP</th>
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 ? (
                  <tr><td colSpan={7} className="py-8 text-center text-slate-400">No PDFs.</td></tr>
                ) : rows.map((p) => (
                  <tr key={p.pdf_id} className="border-b border-slate-100">
                    <td className="py-2 pr-3 font-mono text-xs text-slate-800">{shortId(p.pdf_id)}</td>
                    <td className="py-2 pr-3 font-mono text-xs text-slate-700">{shortId(p.visitor_id)}</td>
                    <td className="py-2 pr-3 text-slate-800">{p.title}</td>
                    <td className="py-2 pr-3 font-mono text-xs text-slate-600">{p.file_name}</td>
                    <td className="py-2 pr-3 text-slate-600">{formatDate(p.created_at)}</td>
                    <td className="py-2 pr-3 font-mono text-xs text-slate-600">{shortId(p.fingerprint_hash)}</td>
                    <td className="py-2 font-mono text-xs text-slate-600">{p.ip_address || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
