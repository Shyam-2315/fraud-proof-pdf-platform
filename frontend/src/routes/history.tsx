import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { getMyHistory, type MyPdfItem } from "@/api/userApi";
import { extractError, formatDate } from "@/api/client";
import { Card } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

export const Route = createFileRoute("/history")({ component: HistoryPage });

function HistoryPage() {
  const [items, setItems] = useState<MyPdfItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const { items } = await getMyHistory();
        setItems(items);
      } catch (e) { setError(extractError(e)); }
      finally { setLoading(false); }
    })();
  }, []);

  return (
    <div className="max-w-5xl mx-auto px-6 py-10 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">My PDFs</h1>
        <p className="text-sm text-slate-600">Your generated documents appear here.</p>
      </div>
      {error && <Alert className="border-red-200 bg-red-50 text-red-800"><AlertDescription>{error}</AlertDescription></Alert>}
      <Card className="p-6 bg-white border-slate-200 shadow-sm">
        {loading ? (
          <p className="text-slate-500">Loading…</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="py-2 pr-4 font-medium">Title</th>
                  <th className="py-2 pr-4 font-medium">File</th>
                  <th className="py-2 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {items.length === 0 ? (
                  <tr><td colSpan={3} className="py-8 text-center text-slate-400">No PDFs generated yet.</td></tr>
                ) : items.map((i) => (
                  <tr key={i.pdf_id} className="border-b border-slate-100">
                    <td className="py-2 pr-4 text-slate-800">{i.title}</td>
                    <td className="py-2 pr-4 font-mono text-xs text-slate-600">{i.file_name}</td>
                    <td className="py-2 text-slate-600">{formatDate(i.created_at)}</td>
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
