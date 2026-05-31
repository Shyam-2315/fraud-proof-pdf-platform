import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { adminApi, type AdminMonitoringResponse } from "@/lib/adminApi";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  StatCard,
  fmtNumber,
} from "@/components/admin/primitives";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const Route = createFileRoute("/admin/monitoring")({
  component: MonitoringPage,
});

function MonitoringPage() {
  const [data, setData] = useState<AdminMonitoringResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        const response = await adminApi.getMonitoring();
        if (!cancelled) setData(response);
      } catch (err: any) {
        if (!cancelled) setError(err?.message || "Failed to load monitoring data.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) return <LoadingState label="Loading monitoring…" />;
  if (error) return <ErrorState message={error} />;
  if (!data) return <EmptyState />;

  const checks = Object.entries(data.checks || {});

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Users" value={fmtNumber(data.total_users)} />
        <StatCard label="Anonymous Visitors" value={fmtNumber(data.total_anonymous_visitors)} />
        <StatCard label="PDFs Generated" value={fmtNumber(data.total_pdfs_generated)} />
        <StatCard label="PDFs Today" value={fmtNumber(data.pdfs_generated_today)} />
        <StatCard
          label="Blocked Visitors"
          value={fmtNumber(data.blocked_visitors)}
          tone="danger"
        />
        <StatCard
          label="Fraud Decisions"
          value={fmtNumber(data.fraud_decisions_count)}
          tone="warning"
        />
        <StatCard
          label="Backend Readiness"
          value={data.backend_readiness_status}
          tone={data.backend_readiness_status === "ready" ? "success" : "danger"}
        />
        <StatCard label="Storage" value={data.storage_health} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Dependency Health</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <HealthRow label="MongoDB" value={data.mongodb_health} />
            <HealthRow label="Redis" value={data.redis_health} />
            <HealthRow label="Storage" value={data.storage_health} />
            <HealthRow label="Readiness" value={data.backend_readiness_status} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Readiness Checks</CardTitle>
        </CardHeader>
        <CardContent>
          {checks.length === 0 ? (
            <EmptyState label="No readiness checks returned." />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {checks.map(([key, value]) => (
                <div key={key} className="rounded-md border p-4">
                  <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    {key.replaceAll("_", " ")}
                  </div>
                  <div className="mt-2 flex items-center justify-between gap-3">
                    <span className="break-all text-sm">{String(value)}</span>
                    <HealthBadge value={value} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function HealthRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="mt-2 flex items-center justify-between gap-3">
        <span className="break-all text-sm">{value}</span>
        <HealthBadge value={value} />
      </div>
    </div>
  );
}

function HealthBadge({ value }: { value: boolean | string }) {
  const ok = value === true || String(value).toLowerCase() === "ok" || value === "ready";
  return ok ? (
    <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
      OK
    </Badge>
  ) : (
    <Badge className="bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300">
      Attention
    </Badge>
  );
}
