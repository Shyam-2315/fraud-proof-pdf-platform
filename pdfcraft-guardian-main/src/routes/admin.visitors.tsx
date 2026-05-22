import { useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { adminApi } from "@/lib/adminApi";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  LoadingState,
  ErrorState,
  EmptyState,
  RiskBadge,
  fmtDate,
  fmtNumber,
} from "@/components/admin/primitives";
import { Input } from "@/components/ui/input";

export const Route = createFileRoute("/admin/visitors")({
  component: VisitorsPage,
});

function arrLen(v: any) {
  if (Array.isArray(v)) return v.length;
  if (typeof v === "number") return v;
  return 0;
}

function VisitorsPage() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        const res = await adminApi.getFraudVisitors();
        const list = Array.isArray(res) ? res : res?.items || res?.visitors || [];
        if (!cancelled) setItems(list);
      } catch (err: any) {
        if (!cancelled) setError(err?.message || "Failed to load visitors.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = items.filter((v) =>
    !search ? true : String(v.visitor_id || "").toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="flex flex-wrap items-center gap-3 p-4">
          <Input
            placeholder="Search visitor ID…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-[260px]"
          />
          <Badge variant="secondary">{filtered.length} visitors</Badge>
        </CardContent>
      </Card>

      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} />
      ) : filtered.length === 0 ? (
        <EmptyState label="No visitors found." />
      ) : (
        <Card>
          <CardContent className="overflow-x-auto p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Visitor ID</TableHead>
                  <TableHead>Free Usage</TableHead>
                  <TableHead>Remaining</TableHead>
                  <TableHead>Risk Score</TableHead>
                  <TableHead>Risk Level</TableHead>
                  <TableHead>Blocked</TableHead>
                  <TableHead>Block Reason</TableHead>
                  <TableHead>LS IDs</TableHead>
                  <TableHead>Sessions</TableHead>
                  <TableHead>Fingerprints</TableHead>
                  <TableHead>IPs</TableHead>
                  <TableHead>UAs</TableHead>
                  <TableHead>First Seen</TableHead>
                  <TableHead>Last Seen</TableHead>
                  <TableHead>Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((v: any, i: number) => (
                  <TableRow key={v.visitor_id || i}>
                    <TableCell className="font-mono text-xs">{v.visitor_id || "—"}</TableCell>
                    <TableCell>{fmtNumber(v.free_usage_count)}</TableCell>
                    <TableCell>{fmtNumber(v.remaining_free_uses)}</TableCell>
                    <TableCell>{v.risk_score ?? "—"}</TableCell>
                    <TableCell>
                      <RiskBadge level={v.risk_level} />
                    </TableCell>
                    <TableCell>
                      {v.is_blocked ? (
                        <Badge className="bg-red-100 text-red-700 hover:bg-red-100 dark:bg-red-950 dark:text-red-300">
                          BLOCKED
                        </Badge>
                      ) : (
                        <Badge variant="secondary">No</Badge>
                      )}
                    </TableCell>
                    <TableCell className="max-w-[200px] truncate text-xs">
                      {v.block_reason || "—"}
                    </TableCell>
                    <TableCell>{arrLen(v.local_storage_ids ?? v.local_storage_id_count)}</TableCell>
                    <TableCell>{arrLen(v.sessions ?? v.session_id_count)}</TableCell>
                    <TableCell>{arrLen(v.fingerprints ?? v.fingerprint_hash_count)}</TableCell>
                    <TableCell>{arrLen(v.ip_addresses ?? v.ips ?? v.ip_address_count)}</TableCell>
                    <TableCell>{arrLen(v.user_agents ?? v.user_agent_count)}</TableCell>
                    <TableCell className="whitespace-nowrap text-xs">
                      {fmtDate(v.first_seen_at ?? v.first_seen)}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-xs">
                      {fmtDate(v.last_seen_at ?? v.last_seen)}
                    </TableCell>
                    <TableCell>
                      <Button asChild size="sm" variant="outline">
                        <Link
                          to="/admin/visitor/$visitorId"
                          params={{ visitorId: v.visitor_id }}
                        >
                          Investigate
                        </Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
