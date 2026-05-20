import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { getVisitors, items } from "@/api/adminApi";
import { useAdminGuard, handleAdminApiError } from "@/components/AdminProtectedRoute";
import { Card } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { RiskBadge } from "@/components/RiskBadge";
import { formatDate, shortId } from "@/api/client";

export const Route = createFileRoute("/admin/visitors")({ component: VisitorsPage });

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type V = any;

function VisitorsPage() {
  useAdminGuard();
  const router = useRouter();
  const [rows, setRows] = useState<V[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try { setRows(items<V>(await getVisitors())); }
      catch (e) { setError(handleAdminApiError(e, router)); }
      finally { setLoading(false); }
    })();
  }, [router]);

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Visitors</h1>
        <p className="text-sm text-slate-500">All tracked visitors with usage and risk metrics.</p>
      </div>
      {error && <Alert className="border-red-200 bg-red-50 text-red-800"><AlertDescription>{error}</AlertDescription></Alert>}
      <Card className="p-6 bg-white border-slate-200 shadow-sm">
        {loading ? <p className="text-slate-500">Loading…</p> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="py-2 pr-3 font-medium">Visitor</th>
                  <th className="py-2 pr-3 font-medium">Used</th>
                  <th className="py-2 pr-3 font-medium">Remaining</th>
                  <th className="py-2 pr-3 font-medium">Risk</th>
                  <th className="py-2 pr-3 font-medium">Score</th>
                  <th className="py-2 pr-3 font-medium">Blocked</th>
                  <th className="py-2 pr-3 font-medium">Reason</th>
                  <th className="py-2 pr-3 font-medium">LS</th>
                  <th className="py-2 pr-3 font-medium">Sess</th>
                  <th className="py-2 pr-3 font-medium">FP</th>
                  <th className="py-2 pr-3 font-medium">IPs</th>
                  <th className="py-2 pr-3 font-medium">UAs</th>
                  <th className="py-2 pr-3 font-medium">First seen</th>
                  <th className="py-2 pr-3 font-medium">Last seen</th>
                  <th className="py-2 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 ? (
                  <tr><td colSpan={15} className="py-8 text-center text-slate-400">No visitors.</td></tr>
                ) : rows.map((v) => (
                  <tr key={v.visitor_id} className="border-b border-slate-100">
                    <td className="py-2 pr-3 font-mono text-xs text-slate-800">{shortId(v.visitor_id)}</td>
                    <td className="py-2 pr-3">{v.free_usage_count}</td>
                    <td className="py-2 pr-3">{v.remaining_free_uses}</td>
                    <td className="py-2 pr-3"><RiskBadge level={v.risk_level} /></td>
                    <td className="py-2 pr-3">{v.risk_score}</td>
                    <td className="py-2 pr-3">{v.is_blocked ? "Yes" : "No"}</td>
                    <td className="py-2 pr-3 text-slate-700">{v.block_reason || "—"}</td>
                    <td className="py-2 pr-3">{v.local_storage_id_count}</td>
                    <td className="py-2 pr-3">{v.session_id_count}</td>
                    <td className="py-2 pr-3">{v.fingerprint_hash_count}</td>
                    <td className="py-2 pr-3">{v.ip_address_count}</td>
                    <td className="py-2 pr-3">{v.user_agent_count}</td>
                    <td className="py-2 pr-3 text-slate-600">{formatDate(v.first_seen_at)}</td>
                    <td className="py-2 pr-3 text-slate-600">{formatDate(v.last_seen_at)}</td>
                    <td className="py-2">
                      <Link to="/admin/visitor/$visitorId" params={{ visitorId: v.visitor_id }}>
                        <Button size="sm" variant="secondary">Investigate</Button>
                      </Link>
                    </td>
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
