import { createFileRoute, useRouter } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { getFraudEvents, items } from "@/api/adminApi";
import { useAdminGuard, handleAdminApiError } from "@/components/AdminProtectedRoute";
import { Card } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RiskBadge, AllowedBadge } from "@/components/RiskBadge";
import { formatDate, shortId } from "@/api/client";

export const Route = createFileRoute("/admin/events")({ component: EventsPage });

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Event = any;

function EventsPage() {
  useAdminGuard();
  const router = useRouter();
  const [rows, setRows] = useState<Event[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [severity, setSeverity] = useState<string>("ALL");
  const [eventType, setEventType] = useState<string>("");
  const [allowed, setAllowed] = useState<string>("ALL");

  useEffect(() => {
    (async () => {
      try { setRows(items<Event>(await getFraudEvents())); }
      catch (e) { setError(handleAdminApiError(e, router)); }
      finally { setLoading(false); }
    })();
  }, [router]);

  const filtered = useMemo(() => rows.filter((r) => {
    if (severity !== "ALL" && String(r.severity).toUpperCase() !== severity) return false;
    if (allowed !== "ALL") {
      const want = allowed === "ALLOWED";
      if (Boolean(r.allowed) !== want) return false;
    }
    if (eventType && !String(r.event_type || "").toLowerCase().includes(eventType.toLowerCase())) return false;
    return true;
  }), [rows, severity, eventType, allowed]);

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Fraud events</h1>
        <p className="text-sm text-slate-500">All detected fraud signals across visitors.</p>
      </div>
      {error && <Alert className="border-red-200 bg-red-50 text-red-800"><AlertDescription>{error}</AlertDescription></Alert>}
      <Card className="p-6 bg-white border-slate-200 shadow-sm">
        <div className="grid sm:grid-cols-3 gap-4 mb-4">
          <div>
            <Label>Severity</Label>
            <Select value={severity} onValueChange={setSeverity}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All</SelectItem>
                <SelectItem value="LOW">LOW</SelectItem>
                <SelectItem value="MEDIUM">MEDIUM</SelectItem>
                <SelectItem value="HIGH">HIGH</SelectItem>
                <SelectItem value="CRITICAL">CRITICAL</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Allowed</Label>
            <Select value={allowed} onValueChange={setAllowed}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All</SelectItem>
                <SelectItem value="ALLOWED">Allowed only</SelectItem>
                <SelectItem value="BLOCKED">Blocked only</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Event type contains</Label>
            <Input value={eventType} onChange={(e) => setEventType(e.target.value)} placeholder="e.g. COOKIE" />
          </div>
        </div>

        {loading ? <p className="text-slate-500">Loading…</p> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="py-2 pr-4 font-medium">Created</th>
                  <th className="py-2 pr-4 font-medium">Visitor</th>
                  <th className="py-2 pr-4 font-medium">Event type</th>
                  <th className="py-2 pr-4 font-medium">Severity</th>
                  <th className="py-2 pr-4 font-medium">Allowed</th>
                  <th className="py-2 pr-4 font-medium">Reason</th>
                  <th className="py-2 pr-4 font-medium">Risk level</th>
                  <th className="py-2 font-medium">IP</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr><td colSpan={8} className="py-8 text-center text-slate-400">No events.</td></tr>
                ) : filtered.map((e) => (
                  <tr key={e.event_id || `${e.visitor_id}-${e.created_at}`} className="border-b border-slate-100 align-top">
                    <td className="py-2 pr-4 text-slate-700">{formatDate(e.created_at)}</td>
                    <td className="py-2 pr-4 font-mono text-xs text-slate-700">{shortId(e.visitor_id)}</td>
                    <td className="py-2 pr-4 font-mono text-xs text-slate-800">{e.event_type}</td>
                    <td className="py-2 pr-4"><RiskBadge level={e.severity} /></td>
                    <td className="py-2 pr-4"><AllowedBadge allowed={Boolean(e.allowed)} /></td>
                    <td className="py-2 pr-4 text-slate-700">{e.reason || e.message || "—"}</td>
                    <td className="py-2 pr-4"><RiskBadge level={e.risk_level} /></td>
                    <td className="py-2 font-mono text-xs text-slate-600">{e.ip_address || e.signals?.ip_address || "—"}</td>
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
