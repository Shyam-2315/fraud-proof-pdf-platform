import { createFileRoute, useRouter } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { getFraudSummary } from "@/api/adminApi";
import { useAdminGuard, handleAdminApiError } from "@/components/AdminProtectedRoute";
import { Card } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

export const Route = createFileRoute("/admin/dashboard")({ component: AdminDashboard });

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Summary = any;

function AdminDashboard() {
  useAdminGuard();
  const router = useRouter();
  const [s, setS] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try { setS(await getFraudSummary()); }
      catch (e) { setError(handleAdminApiError(e, router)); }
      finally { setLoading(false); }
    })();
  }, [router]);

  const cards = s ? [
    { l: "Total visitors", v: s.total_visitors },
    { l: "Blocked visitors", v: s.blocked_visitors },
    { l: "Total PDFs", v: s.total_generated_pdfs ?? s.total_pdfs },
    { l: "Fraud events", v: s.total_fraud_events },
    { l: "Allowed generations", v: s.allowed_pdf_generations ?? s.allowed_generations },
    { l: "Blocked generations", v: s.blocked_pdf_generations ?? s.blocked_generations },
    { l: "High risk visitors", v: s.high_risk_visitors },
    { l: "Medium risk visitors", v: s.medium_risk_visitors },
    { l: "Low risk visitors", v: s.low_risk_visitors },
  ] : [];

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Fraud summary</h1>
        <p className="text-sm text-slate-500">System-wide fraud signals and PDF activity.</p>
      </div>
      {error && <Alert className="border-red-200 bg-red-50 text-red-800"><AlertDescription>{error}</AlertDescription></Alert>}
      {loading ? <p className="text-slate-500">Loading…</p> : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-3 gap-4">
          {cards.map((c) => (
            <Card key={c.l} className="p-5 bg-white border-slate-200 shadow-sm">
              <div className="text-xs uppercase tracking-wide text-slate-500">{c.l}</div>
              <div className="mt-2 text-3xl font-semibold text-slate-900">{c.v ?? 0}</div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
