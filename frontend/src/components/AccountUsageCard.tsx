import type { AccountUsage } from "../api/authApi";

export default function AccountUsageCard({ usage }: { usage: AccountUsage }) {
  const percent = Math.min(100, Math.round((usage.used / Math.max(usage.limit, 1)) * 100));
  return (
    <section className="panel p-5">
      <h2 className="text-xl font-black text-[#10213f]">Monthly usage</h2>
      <p className="mt-1 text-sm font-semibold text-[#52647f]">{usage.month_key}</p>
      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <div>
          <div className="text-2xl font-black text-[#10213f]">{usage.used}</div>
          <div className="text-sm font-bold text-[#52647f]">Used</div>
        </div>
        <div>
          <div className="text-2xl font-black text-[#10213f]">{usage.remaining}</div>
          <div className="text-sm font-bold text-[#52647f]">Remaining</div>
        </div>
        <div>
          <div className="text-2xl font-black text-[#10213f]">{usage.limit}</div>
          <div className="text-sm font-bold text-[#52647f]">Limit</div>
        </div>
      </div>
      <div className="mt-5 h-3 overflow-hidden rounded-full bg-[#e8eef7]">
        <div className="h-full rounded-full bg-[#1459d9]" style={{ width: `${percent}%` }} />
      </div>
    </section>
  );
}
