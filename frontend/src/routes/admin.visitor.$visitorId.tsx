import { createFileRoute, useRouter, Link } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { getVisitorInvestigation, items } from "@/api/adminApi";
import { useAdminGuard, handleAdminApiError } from "@/components/AdminProtectedRoute";
import { Card } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { RiskBadge, AllowedBadge } from "@/components/RiskBadge";
import { formatDate, shortId } from "@/api/client";
import { ArrowLeft } from "lucide-react";

export const Route = createFileRoute("/admin/visitor/$visitorId")({ component: InvestigationPage });

function InvestigationPage() {
  useAdminGuard();
  const router = useRouter();
  const { visitorId } = Route.useParams();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try { setData(await getVisitorInvestigation(visitorId)); }
      catch (e) { setError(handleAdminApiError(e, router)); }
      finally { setLoading(false); }
    })();
  }, [visitorId, router]);

  const profile = data?.visitor || data?.profile || data || {};
  const pdfs = items(data?.pdfs || data?.generated_pdfs);
  const events = items(data?.fraud_events || data?.events);

  const timeline = useMemo(() => {
    const tl: { ts: string; type: "PDF" | "EVENT"; label: string; meta?: string }[] = [];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    pdfs.forEach((p: any) => tl.push({ ts: p.created_at, type: "PDF", label: `PDF: ${p.title || p.file_name}`, meta: p.file_name }));
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    events.forEach((e: any) => tl.push({ ts: e.created_at, type: "EVENT", label: e.event_type || "Event", meta: e.message || e.reason }));
    return tl.sort((a, b) => +new Date(b.ts) - +new Date(a.ts));
  }, [pdfs, events]);

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link to="/admin/visitors" className="text-sm text-slate-500 hover:text-slate-900 inline-flex items-center gap-1">
            <ArrowLeft className="h-3 w-3" /> Back to visitors
          </Link>
          <h1 className="text-2xl font-semibold text-slate-900 mt-1">Visitor investigation</h1>
          <p className="text-sm text-slate-500 font-mono">{visitorId}</p>
        </div>
      </div>

      {error && <Alert className="border-red-200 bg-red-50 text-red-800"><AlertDescription>{error}</AlertDescription></Alert>}

      {loading ? <p className="text-slate-500">Loading…</p> : (
        <>
          <div className="grid lg:grid-cols-3 gap-4">
            <Card className="p-5 bg-white border-slate-200 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-900 mb-3">Profile</h3>
              <dl className="space-y-2 text-sm">
                <Row k="Visitor" v={<span className="font-mono">{shortId(profile.visitor_id || visitorId)}</span>} />
                <Row k="First seen" v={formatDate(profile.first_seen_at)} />
                <Row k="Last seen" v={formatDate(profile.last_seen_at)} />
              </dl>
            </Card>
            <Card className="p-5 bg-white border-slate-200 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-900 mb-3">Usage</h3>
              <dl className="space-y-2 text-sm">
                <Row k="Used" v={`${profile.free_usage_count ?? 0} / ${profile.free_usage_limit ?? 2}`} />
                <Row k="Remaining" v={profile.remaining_free_uses ?? 0} />
                <Row k="PDFs generated" v={pdfs.length} />
              </dl>
            </Card>
            <Card className="p-5 bg-white border-slate-200 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-900 mb-3">Risk</h3>
              <dl className="space-y-2 text-sm">
                <Row k="Risk level" v={<RiskBadge level={profile.risk_level} />} />
                <Row k="Risk score" v={profile.risk_score ?? 0} />
                <Row k="Blocked" v={profile.is_blocked ? "Yes" : "No"} />
                <Row k="Reason" v={profile.block_reason || "—"} />
              </dl>
            </Card>
          </div>

          <Card className="p-6 bg-white border-slate-200 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900 mb-3">Generated PDFs ({pdfs.length})</h2>
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
                  {pdfs.length === 0 ? <tr><td colSpan={3} className="py-6 text-center text-slate-400">No PDFs.</td></tr>
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    : pdfs.map((p: any) => (
                    <tr key={p.pdf_id} className="border-b border-slate-100">
                      <td className="py-2 pr-4 text-slate-800">{p.title}</td>
                      <td className="py-2 pr-4 font-mono text-xs text-slate-600">{p.file_name}</td>
                      <td className="py-2 text-slate-600">{formatDate(p.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card className="p-6 bg-white border-slate-200 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900 mb-3">Fraud events ({events.length})</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="py-2 pr-4 font-medium">Created</th>
                    <th className="py-2 pr-4 font-medium">Event</th>
                    <th className="py-2 pr-4 font-medium">Severity</th>
                    <th className="py-2 pr-4 font-medium">Allowed</th>
                    <th className="py-2 font-medium">Message</th>
                  </tr>
                </thead>
                <tbody>
                  {events.length === 0 ? <tr><td colSpan={5} className="py-6 text-center text-slate-400">No events.</td></tr>
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    : events.map((e: any) => (
                    <tr key={e.event_id} className="border-b border-slate-100">
                      <td className="py-2 pr-4 text-slate-600">{formatDate(e.created_at)}</td>
                      <td className="py-2 pr-4 font-mono text-xs text-slate-800">{e.event_type}</td>
                      <td className="py-2 pr-4"><RiskBadge level={e.severity} /></td>
                      <td className="py-2 pr-4"><AllowedBadge allowed={Boolean(e.allowed)} /></td>
                      <td className="py-2 text-slate-700">{e.message || e.reason || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card className="p-6 bg-white border-slate-200 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900 mb-3">Timeline</h2>
            <ol className="relative border-l border-slate-200 ml-3 space-y-4">
              {timeline.length === 0 ? <p className="text-sm text-slate-400">No activity.</p> :
                timeline.map((t, i) => (
                  <li key={i} className="ml-4">
                    <span className={`absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full ${t.type === "EVENT" ? "bg-red-500" : "bg-indigo-500"}`} />
                    <div className="text-xs text-slate-500">{formatDate(t.ts)} · {t.type}</div>
                    <div className="text-sm text-slate-800 font-medium">{t.label}</div>
                    {t.meta && <div className="text-xs text-slate-500">{t.meta}</div>}
                  </li>
                ))
              }
            </ol>
          </Card>

          <div>
            <Button variant="secondary" onClick={() => router.history.back()}>Back</Button>
          </div>
        </>
      )}
    </div>
  );
}

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-slate-500">{k}</dt>
      <dd className="text-slate-900 font-medium">{v}</dd>
    </div>
  );
}
