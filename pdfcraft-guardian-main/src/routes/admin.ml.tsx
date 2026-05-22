import { useEffect, useState } from "react";
import { createFileRoute, Outlet, useRouterState } from "@tanstack/react-router";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { adminApi } from "@/lib/adminApi";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  StatCard,
  LoadingState,
  ErrorState,
  StatusBadge,
  fmtDate,
  fmtNumber,
} from "@/components/admin/primitives";

export const Route = createFileRoute("/admin/ml")({
  component: MLLayout,
});

function MLLayout() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  if (pathname !== "/admin/ml") return <Outlet />;
  return <MLEnginePage />;
}

function MLEnginePage() {
  const [active, setActive] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [demo, setDemo] = useState(true);
  const [autoActivate, setAutoActivate] = useState(false);
  const [training, setTraining] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminApi.getActiveMLModel();
      setActive(res?.active_model || res?.model || null);
    } catch (err: any) {
      // 404 / empty active is fine — treat as no model
      if (err?.status === 404) setActive(null);
      else setError(err?.message || "Failed to load ML data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const train = async () => {
    setTraining(true);
    try {
      const res = await adminApi.trainMLModel({ demo, auto_activate: autoActivate });
      toast.success("Training completed");
      console.log("Train result:", res);
      load();
    } catch (err: any) {
      toast.error(err?.message || "Training failed.");
    } finally {
      setTraining(false);
    }
  };

  if (loading) return <LoadingState label="Loading ML engine…" />;
  if (error) return <ErrorState message={error} />;

  const m = active || {};
  const metrics = m.metrics || m;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Active Model</CardTitle>
          {!active && (
            <CardDescription>
              No active ML model yet. Rule engine fallback is currently protecting the product.
            </CardDescription>
          )}
        </CardHeader>
        {active && (
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard label="Version" value={m.version || m.model_version || "—"} />
              <StatCard label="Model Type" value={m.model_type || "—"} />
              <StatCard label="Status" value={<StatusBadge status={m.status} />} />
              <StatCard
                label="Last Trained"
                value={fmtDate(m.last_trained_at || m.created_at)}
              />
              <StatCard label="Training Data" value={fmtNumber(m.trained_event_count)} />
              <StatCard label="Positive Labels" value={fmtNumber(m.positive_labels)} />
              <StatCard label="Negative Labels" value={fmtNumber(m.negative_labels)} />
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
              <StatCard label="Accuracy" value={metrics.accuracy ?? "—"} />
              <StatCard label="Precision" value={metrics.precision ?? "—"} />
              <StatCard label="Recall" value={metrics.recall ?? "—"} />
              <StatCard label="F1" value={metrics.f1_score ?? "—"} />
              <StatCard label="ROC AUC" value={metrics.roc_auc ?? "—"} />
            </div>
          </CardContent>
        )}
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Train New Model</CardTitle>
          <CardDescription>Generate a candidate model from collected events.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between rounded-md border p-3">
            <div>
              <Label htmlFor="demo">Demo training</Label>
              <p className="text-xs text-muted-foreground">
                Use synthetic data for quick iteration.
              </p>
            </div>
            <Switch id="demo" checked={demo} onCheckedChange={setDemo} />
          </div>
          <div className="flex items-center justify-between rounded-md border p-3">
            <div>
              <Label htmlFor="auto">Auto activate if metrics pass</Label>
              <p className="text-xs text-muted-foreground">
                Promote candidate to active automatically.
              </p>
            </div>
            <Switch id="auto" checked={autoActivate} onCheckedChange={setAutoActivate} />
          </div>
          <Button onClick={train} disabled={training}>
            {training && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {training ? "Training model…" : "Train Candidate Model"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
