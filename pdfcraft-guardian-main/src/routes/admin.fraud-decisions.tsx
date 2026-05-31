import { useEffect, useState, type FormEvent } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import {
  adminApi,
  type AdminFraudDecisionItem,
  type AdminFraudDecisionListResponse,
} from "@/lib/adminApi";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  RiskBadge,
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

export const Route = createFileRoute("/admin/fraud-decisions")({
  component: FraudDecisionsPage,
});

type Filters = {
  search: string;
  decision: string;
  risk_level: string;
  created_from: string;
  created_to: string;
};

const DEFAULT_FILTERS: Filters = {
  search: "",
  decision: "",
  risk_level: "",
  created_from: "",
  created_to: "",
};

function FraudDecisionsPage() {
  const [data, setData] = useState<AdminFraudDecisionListResponse | null>(null);
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
        const response = await adminApi.getFraudDecisions({
          limit: 100,
          search: activeFilters.search || undefined,
          decision: activeFilters.decision || undefined,
          risk_level: activeFilters.risk_level || undefined,
          created_from: toDateTime(activeFilters.created_from, false),
          created_to: toDateTime(activeFilters.created_to, true),
        });
        if (!cancelled) setData(response);
      } catch (err: any) {
        if (!cancelled) setError(err?.message || "Failed to load fraud decisions.");
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
          <CardTitle className="text-base">Decision Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-3 md:grid-cols-[1fr_150px_150px_160px_160px_auto]" onSubmit={submit}>
            <Input
              placeholder="Visitor, user, action"
              value={filters.search}
              onChange={(event) => setFilters({ ...filters, search: event.target.value })}
            />
            <select
              className="h-10 rounded-md border border-input bg-background px-3 text-sm"
              value={filters.decision}
              onChange={(event) => setFilters({ ...filters, decision: event.target.value })}
            >
              <option value="">Any decision</option>
              <option value="ALLOW">ALLOW</option>
              <option value="ALLOW_LOG">ALLOW_LOG</option>
              <option value="REQUIRE_LOGIN">REQUIRE_LOGIN</option>
              <option value="BLOCK">BLOCK</option>
            </select>
            <select
              className="h-10 rounded-md border border-input bg-background px-3 text-sm"
              value={filters.risk_level}
              onChange={(event) => setFilters({ ...filters, risk_level: event.target.value })}
            >
              <option value="">Any risk</option>
              <option value="LOW">LOW</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="HIGH">HIGH</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
            <Input
              type="date"
              value={filters.created_from}
              onChange={(event) => setFilters({ ...filters, created_from: event.target.value })}
            />
            <Input
              type="date"
              value={filters.created_to}
              onChange={(event) => setFilters({ ...filters, created_to: event.target.value })}
            />
            <Button type="submit">Apply</Button>
          </form>
        </CardContent>
      </Card>

      {loading ? <LoadingState label="Loading fraud decisions…" /> : null}
      {error ? <ErrorState message={error} /> : null}
      {!loading && !error && data ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Fraud Decisions ({fmtNumber(data.total)})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.items.length === 0 ? (
              <EmptyState label="No decisions match these filters." />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Time</TableHead>
                    <TableHead>Visitor</TableHead>
                    <TableHead>User</TableHead>
                    <TableHead>IP</TableHead>
                    <TableHead>Fingerprint</TableHead>
                    <TableHead>Score</TableHead>
                    <TableHead>Risk</TableHead>
                    <TableHead>Decision</TableHead>
                    <TableHead>Reason</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((item) => (
                    <DecisionRow key={item.id} item={item} />
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

function DecisionRow({ item }: { item: AdminFraudDecisionItem }) {
  return (
    <TableRow>
      <TableCell className="whitespace-nowrap text-xs">{fmtDate(item.created_at)}</TableCell>
      <TableCell className="font-mono text-xs">
        {item.visitor_id ? (
          <Link
            to="/admin/visitor/$visitorId"
            params={{ visitorId: item.visitor_id }}
            className="text-primary hover:underline"
          >
            {short(item.visitor_id)}
          </Link>
        ) : (
          "—"
        )}
      </TableCell>
      <TableCell className="font-mono text-xs">{short(item.user_id)}</TableCell>
      <TableCell className="font-mono text-xs">{item.ip_address || "—"}</TableCell>
      <TableCell className="max-w-[160px] truncate font-mono text-xs">
        {item.fingerprint_hash || "—"}
      </TableCell>
      <TableCell className="text-xs">{item.risk_score}</TableCell>
      <TableCell>
        <RiskBadge level={item.risk_level} />
      </TableCell>
      <TableCell>
        <DecisionBadge decision={item.decision} />
      </TableCell>
      <TableCell className="max-w-[280px] truncate text-xs">{item.reason || "—"}</TableCell>
    </TableRow>
  );
}

function DecisionBadge({ decision }: { decision: string }) {
  const value = decision.toUpperCase();
  const tone =
    value === "BLOCK"
      ? "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300"
      : value === "REQUIRE_LOGIN"
        ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
        : "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300";
  return <Badge className={tone}>{value || "—"}</Badge>;
}

function short(value?: string | null) {
  if (!value) return "—";
  return value.length > 12 ? `${value.slice(0, 12)}…` : value;
}

function toDateTime(value: string, endOfDay: boolean) {
  if (!value) return undefined;
  return `${value}T${endOfDay ? "23:59:59" : "00:00:00"}Z`;
}
