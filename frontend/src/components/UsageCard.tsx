import { BarChart3 } from "lucide-react";
import type { VisitorStatus } from "../api/userApi";

export default function UsageCard({ status }: { status: VisitorStatus | null }) {
  const used = status?.free_usage_count ?? 0;
  const limit = status?.free_usage_limit ?? 2;
  const remaining = status?.remaining_free_uses ?? limit;
  const percent = Math.min(100, Math.round((used / Math.max(limit, 1)) * 100));

  return (
    <section className="panel p-5">
      <div className="mb-4 flex items-center gap-3">
        <div className="rounded-lg bg-[#eaf1ff] p-2 text-[#1459d9]">
          <BarChart3 size={22} />
        </div>
        <div>
          <h2 className="text-lg font-black text-[#10213f]">Free usage</h2>
          <p className="text-sm font-semibold text-[#52647f]">
            {status?.message || "You can generate 2 PDFs for free."}
          </p>
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <div>
          <div className="text-2xl font-black text-[#10213f]">{used}</div>
          <div className="text-sm font-bold text-[#52647f]">Used</div>
        </div>
        <div>
          <div className="text-2xl font-black text-[#10213f]">{remaining}</div>
          <div className="text-sm font-bold text-[#52647f]">Remaining</div>
        </div>
        <div>
          <div className="text-2xl font-black text-[#10213f]">{limit}</div>
          <div className="text-sm font-bold text-[#52647f]">Free limit</div>
        </div>
      </div>
      <div className="mt-5 h-3 overflow-hidden rounded-full bg-[#e8eef7]">
        <div className="h-full rounded-full bg-[#1459d9]" style={{ width: `${percent}%` }} />
      </div>
    </section>
  );
}
