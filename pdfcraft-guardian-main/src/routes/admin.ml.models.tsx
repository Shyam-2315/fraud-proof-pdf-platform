import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { toast } from "sonner";
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
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  LoadingState,
  ErrorState,
  EmptyState,
  StatusBadge,
  fmtDate,
  fmtNumber,
} from "@/components/admin/primitives";

export const Route = createFileRoute("/admin/ml/models")({
  component: ModelVersionsPage,
});

function ModelVersionsPage() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<{ action: "activate" | "reject"; id: string } | null>(
    null,
  );
  const [working, setWorking] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminApi.getMLModels();
      const list = Array.isArray(res) ? res : res?.items || res?.models || [];
      setItems(list);
    } catch (err: any) {
      setError(err?.message || "Failed to load models.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const runAction = async () => {
    if (!confirm) return;
    setWorking(true);
    try {
      if (confirm.action === "activate") {
        await adminApi.activateMLModel(confirm.id);
        toast.success("Model activated");
      } else {
        await adminApi.rejectMLModel(confirm.id);
        toast.success("Model rejected");
      }
      setConfirm(null);
      load();
    } catch (err: any) {
      toast.error(err?.message || "Action failed.");
    } finally {
      setWorking(false);
    }
  };

  return (
    <div className="space-y-4">
      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} />
      ) : items.length === 0 ? (
        <EmptyState label="No model versions yet." />
      ) : (
        <Card>
          <CardContent className="overflow-x-auto p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Version</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Events</TableHead>
                  <TableHead>+ Labels</TableHead>
                  <TableHead>− Labels</TableHead>
                  <TableHead>Acc</TableHead>
                  <TableHead>Prec</TableHead>
                  <TableHead>Rec</TableHead>
                  <TableHead>F1</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((m: any, i: number) => {
                  const metrics = m.metrics || m;
                  const id = m.id || m.model_version_id;
                  const status = String(m.status || "").toUpperCase();
                  return (
                    <TableRow key={id || i}>
                      <TableCell className="font-mono text-xs">
                        {m.version || m.model_version || "—"}
                      </TableCell>
                      <TableCell className="text-xs">{m.model_name || m.name || "—"}</TableCell>
                      <TableCell className="text-xs">{m.model_type || "—"}</TableCell>
                      <TableCell>
                        <StatusBadge status={m.status} />
                      </TableCell>
                      <TableCell>{fmtNumber(m.trained_event_count)}</TableCell>
                      <TableCell>{fmtNumber(m.positive_labels)}</TableCell>
                      <TableCell>{fmtNumber(m.negative_labels)}</TableCell>
                      <TableCell>{metrics.accuracy ?? "—"}</TableCell>
                      <TableCell>{metrics.precision ?? "—"}</TableCell>
                      <TableCell>{metrics.recall ?? "—"}</TableCell>
                      <TableCell>{metrics.f1_score ?? "—"}</TableCell>
                      <TableCell className="whitespace-nowrap text-xs">
                        {fmtDate(m.created_at)}
                      </TableCell>
                      <TableCell className="space-x-2">
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={status === "ACTIVE" || !id}
                          onClick={() => setConfirm({ action: "activate", id })}
                        >
                          Activate
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={status === "REJECTED" || !id}
                          onClick={() => setConfirm({ action: "reject", id })}
                        >
                          Reject
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <AlertDialog open={!!confirm} onOpenChange={(o) => !o && setConfirm(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {confirm?.action === "activate" ? "Activate model?" : "Reject model?"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {confirm?.action === "activate"
                ? "This will promote the candidate to be the active production model."
                : "This will mark the model version as rejected and unusable."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={working}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={runAction} disabled={working}>
              {working ? "Working…" : "Confirm"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
