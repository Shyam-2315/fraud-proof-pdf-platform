import { useEffect, useMemo, useState } from "react";
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
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  LoadingState,
  ErrorState,
  EmptyState,
  RiskBadge,
  AllowedBadge,
  fmtDate,
} from "@/components/admin/primitives";
import { Badge } from "@/components/ui/badge";

export const Route = createFileRoute("/admin/events")({
  component: EventsPage,
});

function EventsPage() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [severity, setSeverity] = useState("all");
  const [type, setType] = useState("");
  const [allowed, setAllowed] = useState("all");
  const [visitor, setVisitor] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        const res = await adminApi.getFraudEvents({ limit: 200 });
        const list = Array.isArray(res) ? res : res?.items || res?.events || [];
        if (!cancelled) setItems(list);
      } catch (err: any) {
        if (!cancelled) setError(err?.message || "Failed to load events.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const eventTypes = useMemo(
    () => Array.from(new Set(items.map((e) => e.event_type).filter(Boolean))),
    [items],
  );

  const filtered = items.filter((e) => {
    if (severity !== "all" && String(e.severity).toUpperCase() !== severity) return false;
    if (type && e.event_type !== type) return false;
    if (allowed === "allowed" && e.allowed !== true) return false;
    if (allowed === "blocked" && e.allowed !== false) return false;
    if (visitor && !String(e.visitor_id || "").toLowerCase().includes(visitor.toLowerCase()))
      return false;
    return true;
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="flex flex-wrap gap-3 p-4">
          <Select value={severity} onValueChange={setSeverity}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Severity" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All severities</SelectItem>
              <SelectItem value="LOW">Low</SelectItem>
              <SelectItem value="MEDIUM">Medium</SelectItem>
              <SelectItem value="HIGH">High</SelectItem>
              <SelectItem value="CRITICAL">Critical</SelectItem>
            </SelectContent>
          </Select>
          <Select value={type || "all"} onValueChange={(v) => setType(v === "all" ? "" : v)}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Event type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All event types</SelectItem>
              {eventTypes.map((t) => (
                <SelectItem key={t} value={t}>
                  {t}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={allowed} onValueChange={setAllowed}>
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Allowed & blocked</SelectItem>
              <SelectItem value="allowed">Allowed</SelectItem>
              <SelectItem value="blocked">Blocked</SelectItem>
            </SelectContent>
          </Select>
          <Input
            placeholder="Search visitor ID…"
            value={visitor}
            onChange={(e) => setVisitor(e.target.value)}
            className="w-[220px]"
          />
        </CardContent>
      </Card>

      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} />
      ) : filtered.length === 0 ? (
        <EmptyState label="No matching fraud events." />
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Created At</TableHead>
                  <TableHead>Visitor ID</TableHead>
                  <TableHead>Event Type</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Allowed</TableHead>
                  <TableHead>Reason</TableHead>
                  <TableHead>Risk Level</TableHead>
                  <TableHead>IP Address</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((e: any, i: number) => (
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
                          {e.visitor_id}
                        </Link>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell className="text-xs">{e.event_type || "—"}</TableCell>
                    <TableCell>
                      <RiskBadge level={e.severity} />
                    </TableCell>
                    <TableCell>
                      <AllowedBadge allowed={e.allowed} />
                    </TableCell>
                    <TableCell className="max-w-[260px] truncate text-xs">
                      {e.reason || "—"}
                    </TableCell>
                    <TableCell>
                      <RiskBadge level={e.risk_level} />
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {e.ip_address || e.ip || "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
      <p className="text-xs text-muted-foreground">
        Showing {filtered.length} of {items.length} events.{" "}
        {filtered.length !== items.length && <Badge variant="secondary">filtered</Badge>}
      </p>
    </div>
  );
}
