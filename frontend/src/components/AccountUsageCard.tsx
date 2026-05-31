import type { AccountUsage } from "../api/authApi";

export default function AccountUsageCard({ usage }: { usage: AccountUsage }) {
  const percent = Math.min(100, Math.round((usage.used / Math.max(usage.limit, 1)) * 100));
  const period = `${formatDate(usage.billing_period_start)} - ${formatDate(usage.billing_period_end)}`;
  return (
    <section className="panel p-5">
      <h2 className="text-xl font-black text-[#10213f]">Monthly usage</h2>
      <p className="mt-1 text-sm font-semibold text-[#52647f]">
        {usage.month_key} billing period
      </p>
      <p className="mt-1 text-xs font-bold uppercase text-[#7b8aa3]" style={{ letterSpacing: "0.18em" }}>
        {period}
      </p>
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
      {usage.requires_upgrade ? (
        <p className="mt-4 rounded-lg bg-[#fff4d8] p-3 text-sm font-black text-[#765000]">
          You have reached your monthly plan limit. Upgrade options are available on the pricing page.
        </p>
      ) : null}
    </section>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}
