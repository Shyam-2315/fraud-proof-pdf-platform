import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { adminApi } from "@/lib/adminApi";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { LoadingState, ErrorState, EmptyState, fmtDate } from "@/components/admin/primitives";

export const Route = createFileRoute("/admin/audit-logs")({
  component: AuditLogsPage,
});

function AuditLogsPage() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await adminApi.getAuditLogs();
        const list = Array.isArray(res) ? res : res?.items || res?.logs || [];
        if (!cancelled) setItems(list);
      } catch (err: any) {
        if (!cancelled) setError(err?.message || "Failed to load audit logs.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (items.length === 0) return <EmptyState label="No audit logs yet." />;

  return (
    <Card>
      <CardContent className="overflow-x-auto p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Created At</TableHead>
              <TableHead>Action</TableHead>
              <TableHead>Target Type</TableHead>
              <TableHead>Target ID</TableHead>
              <TableHead>Metadata</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((log: any, i: number) => (
              <TableRow key={log.id || i}>
                <TableCell className="whitespace-nowrap text-xs">
                  {fmtDate(log.created_at)}
                </TableCell>
                <TableCell className="text-xs font-medium">{log.action || "—"}</TableCell>
                <TableCell className="text-xs">{log.target_type || "—"}</TableCell>
                <TableCell className="font-mono text-xs">{log.target_id || "—"}</TableCell>
                <TableCell>
                  {log.metadata ? (
                    <pre className="max-w-[420px] overflow-x-auto rounded bg-muted p-2 text-[11px] leading-snug">
                      {typeof log.metadata === "string"
                        ? log.metadata
                        : JSON.stringify(log.metadata, null, 2)}
                    </pre>
                  ) : (
                    <span className="text-xs text-muted-foreground">—</span>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
