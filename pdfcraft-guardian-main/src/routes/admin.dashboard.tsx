import { useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { adminApi } from "@/lib/adminApi";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  StatCard,
  LoadingState,
  ErrorState,
  EmptyState,
  RiskBadge,
  AllowedBadge,
  fmtDate,
  fmtNumber,
} from "@/components/admin/primitives";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export const Route = createFileRoute("/admin/dashboard")({
  component: DashboardPage,
});

function get<T = any>(obj: any, ...keys: string[]): T | undefined {
  for (const k of keys) {
    if (obj && obj[k] !== undefined && obj[k] !== null) return obj[k];
  }
  return undefined;
}

function DashboardPage() {
  const [data, setData] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        const [summary, evtRes] = await Promise.allSettled([
          adminApi.getFraudSummary(),
          adminApi.getFraudEvents({ limit: 10 }),
        ]);
        if (cancelled) return;
        if (summary.status === "fulfilled") setData(summary.value);
        else throw summary.reason;
        if (evtRes.status === "fulfilled") {
          const list = Array.isArray(evtRes.value)
            ? evtRes.value
            : evtRes.value?.items || evtRes.value?.events || [];
          setEvents(list);
        }
      } catch (err: any) {
        if (!cancelled) setError(err?.message || "Failed to load dashboard.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) return <LoadingState label="Loading dashboard…" />;
  if (error) return <ErrorState message={error} />;
  if (!data) return <EmptyState />;

  const s = data;
  const blocked = events.filter((e) => e.allowed === false);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Visitors" value={fmtNumber(get(s, "total_visitors", "visitors_total"))} />
        <StatCard
          label="Blocked Visitors"
          value={fmtNumber(get(s, "blocked_visitors", "visitors_blocked"))}
          tone="danger"
        />
        <StatCard
          label="Total Generated PDFs"
          value={fmtNumber(
            get(s, "total_generated_pdfs", "total_pdfs", "pdfs_total", "generated_pdfs"),
          )}
        />
        <StatCard
          label="Fraud Events"
          value={fmtNumber(get(s, "total_fraud_events", "fraud_events", "events_total"))}
        />
        <StatCard
          label="Allowed Generations"
          value={fmtNumber(get(s, "allowed_pdf_generations", "allowed_generations", "allowed"))}
          tone="success"
        />
        <StatCard
          label="Blocked Generations"
          value={fmtNumber(get(s, "blocked_pdf_generations", "blocked_generations", "blocked"))}
          tone="danger"
        />
        <StatCard
          label="High Risk Visitors"
          value={fmtNumber(get(s, "high_risk_visitors", "high_risk"))}
          tone="warning"
        />
        <StatCard
          label="Medium Risk Visitors"
          value={fmtNumber(get(s, "medium_risk_visitors", "medium_risk"))}
        />
        <StatCard
          label="Low Risk Visitors"
          value={fmtNumber(get(s, "low_risk_visitors", "low_risk"))}
          tone="success"
        />
        <StatCard
          label="ML Decisions Today"
          value={fmtNumber(get(s, "ml_decisions_today", "ml_decisions"))}
        />
        <StatCard
          label="Identity Links Created"
          value={fmtNumber(get(s, "identity_links_created", "identity_links"))}
        />
        <StatCard
          label="Training Events"
          value={fmtNumber(get(s, "training_events_collected", "training_events"))}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent Fraud Events</CardTitle>
          </CardHeader>
          <CardContent>
            {events.length === 0 ? (
              <EmptyState label="No recent events." />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Time</TableHead>
                    <TableHead>Visitor</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Allowed</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {events.slice(0, 8).map((e: any, i: number) => (
                    <TableRow key={e.id || i}>
                      <TableCell className="whitespace-nowrap text-xs">
                        {fmtDate(e.created_at)}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {e.visitor_id ? (
                          <Link
                            to="/admin/visitor/$visitorId"
                            params={{ visitorId: e.visitor_id }}
                            className="text-primary hover:underline"
                          >
                            {String(e.visitor_id).slice(0, 12)}…
                          </Link>
                        ) : (
                          "—"
                        )}
                      </TableCell>
                      <TableCell className="text-xs">{e.event_type || "—"}</TableCell>
                      <TableCell>
                        <AllowedBadge allowed={e.allowed} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent Blocked Attempts</CardTitle>
          </CardHeader>
          <CardContent>
            {blocked.length === 0 ? (
              <EmptyState label="No blocked attempts." />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Time</TableHead>
                    <TableHead>Visitor</TableHead>
                    <TableHead>Reason</TableHead>
                    <TableHead>Risk</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {blocked.slice(0, 8).map((e: any, i: number) => (
                    <TableRow key={e.id || i}>
                      <TableCell className="whitespace-nowrap text-xs">
                        {fmtDate(e.created_at)}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {e.visitor_id ? String(e.visitor_id).slice(0, 12) + "…" : "—"}
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate text-xs">
                        {e.reason || "—"}
                      </TableCell>
                      <TableCell>
                        <RiskBadge level={e.risk_level} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
