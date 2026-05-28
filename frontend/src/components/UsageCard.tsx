import { BarChart3 } from "lucide-react";
import { Link } from "react-router-dom";
import {
  getVisitorStatusMessage,
  getVisitorUsageSnapshot,
  type VisitorStatus,
} from "../api/userApi";

export default function UsageCard({
  status,
  showLoginCta = false,
}: {
  status: VisitorStatus | null;
  showLoginCta?: boolean;
}) {
  const { used, remaining, freeLimit } = getVisitorUsageSnapshot(status);
  const limit = freeLimit;
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
            {getVisitorStatusMessage(status)}
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
      {showLoginCta ? (
        <div className="mt-5 rounded-lg border border-[#f0d58a] bg-[#fff8e4] p-4">
          <p className="text-sm font-bold text-[#765000]">
            Free limit reached. Please log in to continue.
          </p>
          <div className="mt-3 flex flex-wrap gap-3">
            <Link className="btn-primary" state={{ from: "/generate" }} to="/login">Login</Link>
            <Link className="btn-secondary" state={{ from: "/generate" }} to="/signup">Sign Up</Link>
          </div>
        </div>
      ) : null}
    </section>
  );
}
