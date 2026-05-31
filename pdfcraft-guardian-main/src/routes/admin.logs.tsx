import { useEffect, useState, type FormEvent } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  adminApi,
  type AdminRequestLogItem,
  type AdminRequestLogListResponse,
} from "@/lib/adminApi";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  fmtDate,
  fmtNumber,
} from "@/components/admin/primitives";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export const Route = createFileRoute("/admin/logs")({
  component: RequestLogsPage,
});

type Filters = {
  method: string;
  status_code: string;
  path: string;
};

const DEFAULT_FILTERS: Filters = {
  method: "",
  status_code: "",
  path: "",
};

function RequestLogsPage() {
  const [data, setData] = useState<AdminRequestLogListResponse | null>(null);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [activeFilters, setActiveFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await adminApi.getRequestLogs({
          limit: 100,
          method: activeFilters.method.toUpperCase() || undefined,
          status_code: activeFilters.status_code ? Number(activeFilters.status_code) : undefined,
          path: activeFilters.path || undefined,
        });
        if (!cancelled) setData(response);
      } catch (err: any) {
        if (!cancelled) setError(err?.message || "Failed to load request logs.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [activeFilters]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setActiveFilters(filters);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Request Log Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-3 md:grid-cols-[120px_140px_1fr_auto]" onSubmit={submit}>
            <Input
              placeholder="Method"
              value={filters.method}
              onChange={(event) => setFilters({ ...filters, method: event.target.value })}
            />
            <Input
              inputMode="numeric"
              placeholder="Status"
              value={filters.status_code}
              onChange={(event) => setFilters({ ...filters, status_code: event.target.value })}
            />
            <Input
              placeholder="Path contains"
              value={filters.path}
              onChange={(event) => setFilters({ ...filters, path: event.target.value })}
            />
            <Button type="submit">Apply</Button>
          </form>
        </CardContent>
      </Card>

      {loading ? <LoadingState label="Loading request logs…" /> : null}
      {error ? <ErrorState message={error} /> : null}
      {!loading && !error && data ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Recent API Requests ({fmtNumber(data.total)})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.items.length === 0 ? (
              <EmptyState label="No request logs match these filters." />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Time</TableHead>
                    <TableHead>Request ID</TableHead>
                    <TableHead>Method</TableHead>
                    <TableHead>Path</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead>Client IP</TableHead>
                    <TableHead>Block Reason</TableHead>
                    <TableHead>Risk</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((item) => (
                    <RequestLogRow key={`${item.request_id}-${item.created_at}`} item={item} />
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

function RequestLogRow({ item }: { item: AdminRequestLogItem }) {
  return (
    <TableRow>
      <TableCell className="whitespace-nowrap text-xs">{fmtDate(item.created_at)}</TableCell>
      <TableCell className="max-w-[160px] truncate font-mono text-xs">
        {item.request_id || "—"}
      </TableCell>
      <TableCell>
        <Badge variant="outline">{item.method}</Badge>
      </TableCell>
      <TableCell className="max-w-[260px] truncate font-mono text-xs">{item.path}</TableCell>
      <TableCell>
        <StatusCodeBadge status={item.status_code} />
      </TableCell>
      <TableCell className="whitespace-nowrap text-xs">{item.duration_ms} ms</TableCell>
      <TableCell className="font-mono text-xs">{item.client_ip || "—"}</TableCell>
      <TableCell className="max-w-[200px] truncate text-xs">
        {item.block_reason || "—"}
      </TableCell>
      <TableCell className="text-xs">{item.fraud_score ?? "—"}</TableCell>
    </TableRow>
  );
}

function StatusCodeBadge({ status }: { status: number }) {
  const tone =
    status >= 500
      ? "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300"
      : status >= 400
        ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
        : "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300";
  return <Badge className={tone}>{status}</Badge>;
}
