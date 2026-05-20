import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { getVisitorStatus, type VisitorStatus } from "@/api/userApi";
import { extractError } from "@/api/client";
import { Card } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/usage")({ component: UsagePage });

function UsagePage() {
  const [status, setStatus] = useState<VisitorStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try { setStatus(await getVisitorStatus()); }
      catch (e) { setError(extractError(e)); }
      finally { setLoading(false); }
    })();
  }, []);

  const used = status?.free_usage_count ?? 0;
  const limit = status?.free_usage_limit ?? 2;
  const remaining = status?.remaining_free_uses ?? Math.max(0, limit - used);
  const pct = limit > 0 ? Math.min(100, (used / limit) * 100) : 0;

  return (
    <div className="max-w-3xl mx-auto px-6 py-10 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">My Usage</h1>
        <p className="text-sm text-slate-600">Track your free PDF generation limit.</p>
      </div>
      {error && <Alert className="border-red-200 bg-red-50 text-red-800"><AlertDescription>{error}</AlertDescription></Alert>}
      {loading ? (
        <p className="text-slate-500">Loading…</p>
      ) : status ? (
        <Card className="p-6 bg-white border-slate-200 shadow-sm space-y-5">
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-slate-600">Free PDFs Used</span>
              <span className="font-medium text-slate-900">{used} / {limit}</span>
            </div>
            <Progress value={pct} />
          </div>
          <dl className="grid grid-cols-3 gap-4 text-sm">
            <Stat label="Used" value={used} />
            <Stat label="Remaining" value={remaining} />
            <Stat label="Free Limit" value={limit} />
          </dl>
          {status.is_blocked && (
            <div className="rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-800 space-y-3">
              <p>You have used your free PDF generations. Please log in to continue.</p>
              <Link to="/"><Button size="sm" className="bg-red-600 hover:bg-red-700 text-white">Login / Signup</Button></Link>
            </div>
          )}
          {!status.is_blocked && remaining === 0 && (
            <p className="text-sm text-slate-600">An account is required to continue generating PDFs after the free limit.</p>
          )}
        </Card>
      ) : null}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-md bg-slate-50 border border-slate-200 p-3">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 font-medium text-slate-900">{value}</div>
    </div>
  );
}
