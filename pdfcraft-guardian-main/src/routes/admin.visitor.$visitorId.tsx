import { useCallback, useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { toast } from "sonner";
import { ArrowLeft } from "lucide-react";
import { adminApi } from "@/lib/adminApi";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  StatCard,
  LoadingState,
  ErrorState,
  AllowedBadge,
  RiskBadge,
  fmtDate,
  fmtNumber,
} from "@/components/admin/primitives";

export const Route = createFileRoute("/admin/visitor/$visitorId")({
  component: VisitorInvestigationPage,
});

function arrLen(v: any) {
  if (Array.isArray(v)) return v.length;
  if (typeof v === "number") return v;
  return 0;
}

function VisitorInvestigationPage() {
  const { visitorId } = Route.useParams();
  const [profile, setProfile] = useState<any>(null);
  const [decisions, setDecisions] = useState<any[]>([]);
  const [features, setFeatures] = useState<any>(null);
  const [links, setLinks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notes, setNotes] = useState("");
  const [labeling, setLabeling] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [p, d, f, l] = await Promise.allSettled([
        adminApi.getVisitorInvestigation(visitorId),
        adminApi.getFraudDecisions(visitorId),
        adminApi.getFraudFeatures(visitorId),
        adminApi.getIdentityLinks(visitorId),
      ]);
      if (p.status === "fulfilled") setProfile(p.value);
      else throw p.reason;
      if (d.status === "fulfilled") {
        const v = d.value;
        setDecisions(Array.isArray(v) ? v : v?.items || v?.decisions || []);
      }
      if (f.status === "fulfilled") setFeatures(f.value);
      if (l.status === "fulfilled") {
        const v = l.value;
        setLinks(Array.isArray(v) ? v : v?.items || v?.links || []);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load investigation.");
    } finally {
      setLoading(false);
    }
  }, [visitorId]);

  useEffect(() => {
    load();
  }, [load]);

  const submitLabel = async (label: number) => {
    setLabeling(true);
    try {
      await adminApi.labelVisitor({ visitor_id: visitorId, label, notes });
      toast.success(label === 1 ? "Marked as suspicious" : "Marked as normal");
      setNotes("");
      load();
    } catch (err: any) {
      toast.error(err?.message || "Failed to label visitor.");
    } finally {
      setLabeling(false);
    }
  };

  if (loading) return <LoadingState label="Loading investigation…" />;
  if (error) return <ErrorState message={error} />;
  if (!profile) return <ErrorState message="Visitor not found." />;

  const v = profile.visitor || profile;
  const profileFeatures = profile.feature_snapshots || [];
  const featureItems = Array.isArray(features?.items)
    ? features.items
    : Array.isArray(profileFeatures)
      ? profileFeatures
      : [];
  const featureList = features?.features || featureItems[0]?.features || featureItems[0] || features || {};
  const pdfs = profile.pdfs || profile.generated_pdfs || [];
  const fraudEvents = profile.fraud_events || [];
  const fraudDecisions =
    decisions.length > 0 ? decisions : profile.fraud_decisions || profile.fraud_decision_history || [];
  const identityLinks = links.length > 0 ? links : profile.identity_graph_links || profile.linked_visitors || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Button asChild variant="ghost" size="sm">
          <Link to="/admin/visitors">
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to visitors
          </Link>
        </Button>
      </div>

      {/* Profile */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Visitor Profile</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 text-sm">
          <Field label="Visitor ID" value={<span className="font-mono">{v.visitor_id}</span>} />
          <Field label="First Seen" value={fmtDate(v.first_seen_at ?? v.first_seen)} />
          <Field label="Last Seen" value={fmtDate(v.last_seen_at ?? v.last_seen)} />
          <Field
            label="Blocked"
            value={
              v.is_blocked ? (
                <Badge className="bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300">
                  BLOCKED
                </Badge>
              ) : (
                <Badge variant="secondary">No</Badge>
              )
            }
          />
          <Field label="Block Reason" value={v.block_reason || "—"} />
          <Field label="Risk Score" value={v.risk_score ?? "—"} />
          <Field label="Risk Level" value={<RiskBadge level={v.risk_level} />} />
        </CardContent>
      </Card>

      {/* Identity Signals + Usage Summary */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Identity Signals</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            <StatCard label="Local Storage IDs" value={arrLen(v.local_storage_ids ?? v.local_storage_id_count)} />
            <StatCard label="Sessions" value={arrLen(v.sessions ?? v.session_id_count)} />
            <StatCard label="Fingerprints" value={arrLen(v.fingerprints ?? v.fingerprint_hash_count)} />
            <StatCard label="IP Addresses" value={arrLen(v.ip_addresses ?? v.ips ?? v.ip_address_count)} />
            <StatCard label="User Agents" value={arrLen(v.user_agents ?? v.user_agent_count)} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Usage Summary</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            <StatCard label="Free Usage" value={fmtNumber(v.free_usage_count)} />
            <StatCard label="Free Limit" value={fmtNumber(v.free_limit ?? v.free_usage_limit)} />
            <StatCard label="Remaining" value={fmtNumber(v.remaining_free_uses)} />
            <StatCard label="Generated PDFs" value={fmtNumber(pdfs.length || v.pdf_count)} />
          </CardContent>
        </Card>
      </div>

      {/* Fraud Events */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Fraud Events</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {fraudEvents.length === 0 ? (
            <p className="p-6 text-sm text-muted-foreground">No fraud events recorded.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>Event Type</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Allowed</TableHead>
                  <TableHead>Reason</TableHead>
                  <TableHead>Risk</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {fraudEvents.map((event: any, i: number) => (
                  <TableRow key={event.id || i}>
                    <TableCell className="whitespace-nowrap text-xs">
                      {fmtDate(event.created_at)}
                    </TableCell>
                    <TableCell className="text-xs">{event.event_type || "—"}</TableCell>
                    <TableCell>
                      <RiskBadge level={event.severity} />
                    </TableCell>
                    <TableCell>
                      <AllowedBadge allowed={event.allowed} />
                    </TableCell>
                    <TableCell className="max-w-[300px] truncate text-xs">
                      {event.reason || "—"}
                    </TableCell>
                    <TableCell>
                      <RiskBadge level={event.risk_level} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Fraud Decisions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Fraud Decisions</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {fraudDecisions.length === 0 ? (
            <p className="p-6 text-sm text-muted-foreground">No decisions recorded.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>Decision</TableHead>
                  <TableHead>Final Risk</TableHead>
                  <TableHead>Rule</TableHead>
                  <TableHead>ML Prob</TableHead>
                  <TableHead>Anomaly</TableHead>
                  <TableHead>Reasons</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {fraudDecisions.map((d: any, i: number) => (
                  <TableRow key={d.id || i}>
                    <TableCell className="whitespace-nowrap text-xs">
                      {fmtDate(d.created_at)}
                    </TableCell>
                    <TableCell>{d.decision || "—"}</TableCell>
                    <TableCell>{d.final_risk_score ?? "—"}</TableCell>
                    <TableCell>{d.rule_score ?? "—"}</TableCell>
                    <TableCell>{d.ml_fraud_probability ?? "—"}</TableCell>
                    <TableCell>{d.anomaly_score ?? "—"}</TableCell>
                    <TableCell className="max-w-[300px] truncate text-xs">
                      {Array.isArray(d.reasons) ? d.reasons.join(", ") : d.reasons || "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Identity Links */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Identity Links</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {identityLinks.length === 0 ? (
            <p className="p-6 text-sm text-muted-foreground">No identity links.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Source</TableHead>
                  <TableHead>Target</TableHead>
                  <TableHead>Link Type</TableHead>
                  <TableHead>Confidence</TableHead>
                  <TableHead>Matched Signals</TableHead>
                  <TableHead>Reason</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {identityLinks.map((l: any, i: number) => (
                  <TableRow key={l.id || i}>
                    <TableCell className="font-mono text-xs">
                      {l.source_visitor_id || l.source || "—"}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {l.target_visitor_id || l.target || "—"}
                    </TableCell>
                    <TableCell>{l.link_type || "—"}</TableCell>
                    <TableCell>{l.confidence ?? "—"}</TableCell>
                    <TableCell className="text-xs">
                      {Array.isArray(l.matched_signals)
                        ? l.matched_signals.join(", ")
                        : l.matched_signals || "—"}
                    </TableCell>
                    <TableCell className="max-w-[260px] truncate text-xs">
                      {l.reason || "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Feature Snapshots */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Feature Snapshots</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {[
              "num_cookie_ids",
              "num_session_ids",
              "num_ip_addresses",
              "blocked_attempts",
              "webdriver_detected",
              "api_only_usage_pattern",
              "identity_link_confidence_max",
            ].map((k) => (
              <StatCard
                key={k}
                label={k.replace(/_/g, " ")}
                value={String(featureList[k] ?? "—")}
              />
            ))}
          </div>
          {featureItems.length > 1 && (
            <p className="mt-3 text-xs text-muted-foreground">
              Showing the latest feature snapshot from {featureItems.length} available snapshots.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Generated PDFs */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Generated PDFs</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {pdfs.length === 0 ? (
            <p className="p-6 text-sm text-muted-foreground">No PDFs generated.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead>File Name</TableHead>
                  <TableHead>Created At</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pdfs.map((p: any, i: number) => (
                  <TableRow key={p.id || i}>
                    <TableCell className="text-xs">{p.title || "—"}</TableCell>
                    <TableCell className="font-mono text-xs">
                      {p.file_name || p.filename || "—"}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-xs">
                      {fmtDate(p.created_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Admin Label Controls */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Admin Label Controls</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Textarea
            placeholder="Notes (optional)…"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
          />
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              onClick={() => submitLabel(0)}
              disabled={labeling}
            >
              Mark Normal
            </Button>
            <Button
              variant="destructive"
              onClick={() => submitLabel(1)}
              disabled={labeling}
            >
              Mark Suspicious
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 text-sm">{value}</div>
    </div>
  );
}
