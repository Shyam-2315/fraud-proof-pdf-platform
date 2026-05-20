import { Badge } from "@/components/ui/badge";

export function RiskBadge({ level }: { level?: string | null }) {
  const l = (level || "").toUpperCase();
  const cls =
    l === "CRITICAL" ? "bg-red-200 text-red-900 border-red-300"
    : l === "HIGH" ? "bg-red-100 text-red-700 border-red-200"
    : l === "MEDIUM" ? "bg-yellow-100 text-yellow-800 border-yellow-200"
    : l === "LOW" ? "bg-emerald-100 text-emerald-700 border-emerald-200"
    : "bg-slate-100 text-slate-700 border-slate-200";
  return <Badge className={cls}>{l || "—"}</Badge>;
}

export function AllowedBadge({ allowed }: { allowed?: boolean }) {
  return allowed
    ? <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200">ALLOWED</Badge>
    : <Badge className="bg-red-100 text-red-700 border-red-200">BLOCKED</Badge>;
}
