import { ReactNode } from "react";
import { AlertCircle, Inbox, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function StatCard({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: "default" | "success" | "warning" | "danger";
}) {
  const toneClass = {
    default: "text-foreground",
    success: "text-emerald-600 dark:text-emerald-400",
    warning: "text-amber-600 dark:text-amber-400",
    danger: "text-red-600 dark:text-red-400",
  }[tone];
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className={cn("text-2xl font-semibold", toneClass)}>{value ?? "—"}</div>
        {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
      </CardContent>
    </Card>
  );
}

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 rounded-md border bg-card p-10 text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" /> {label}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-3 rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
      <AlertCircle className="h-4 w-4 shrink-0" />
      <span>{message}</span>
    </div>
  );
}

export function EmptyState({ label = "No data available." }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-md border bg-card p-10 text-sm text-muted-foreground">
      <Inbox className="h-5 w-5" />
      <span>{label}</span>
    </div>
  );
}

export function RiskBadge({ level }: { level?: string | null }) {
  if (!level) return <span className="text-muted-foreground">—</span>;
  const l = String(level).toUpperCase();
  const cls =
    l === "CRITICAL"
      ? "bg-red-600 text-white hover:bg-red-600"
      : l === "HIGH"
        ? "bg-red-100 text-red-700 hover:bg-red-100 dark:bg-red-950 dark:text-red-300"
        : l === "MEDIUM"
          ? "bg-amber-100 text-amber-800 hover:bg-amber-100 dark:bg-amber-950 dark:text-amber-300"
          : l === "LOW"
            ? "bg-emerald-100 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-950 dark:text-emerald-300"
            : "bg-muted text-foreground";
  return <Badge className={cn("font-medium", cls)}>{l}</Badge>;
}

export function AllowedBadge({ allowed }: { allowed?: boolean | null }) {
  if (allowed === null || allowed === undefined)
    return <span className="text-muted-foreground">—</span>;
  return allowed ? (
    <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-950 dark:text-emerald-300">
      ALLOWED
    </Badge>
  ) : (
    <Badge className="bg-red-100 text-red-700 hover:bg-red-100 dark:bg-red-950 dark:text-red-300">
      BLOCKED
    </Badge>
  );
}

export function StatusBadge({ status }: { status?: string | null }) {
  if (!status) return <span className="text-muted-foreground">—</span>;
  const s = String(status).toUpperCase();
  const map: Record<string, string> = {
    ACTIVE: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
    CANDIDATE: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
    REJECTED: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
    FAILED: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
    ARCHIVED: "bg-muted text-muted-foreground",
    TRAINING: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  };
  return <Badge className={cn("font-medium", map[s] || "bg-muted")}>{s}</Badge>;
}

export function fmtDate(value?: string | number | null): string {
  if (!value) return "—";
  try {
    const d = new Date(value);
    if (isNaN(d.getTime())) return String(value);
    return d.toLocaleString();
  } catch {
    return String(value);
  }
}

export function fmtNumber(value?: number | null): string {
  if (value === null || value === undefined) return "—";
  return Number(value).toLocaleString();
}
