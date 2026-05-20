import type { LucideIcon } from "lucide-react";

export default function StatCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: number | string;
  icon: LucideIcon;
}) {
  return (
    <div className="panel p-5">
      <div className="mb-4 flex items-center justify-between gap-4">
        <div className="rounded-lg bg-[#eaf1ff] p-2 text-[#1459d9]">
          <Icon size={22} />
        </div>
      </div>
      <div className="text-3xl font-black text-[#10213f]">{value}</div>
      <div className="mt-1 text-sm font-bold text-[#52647f]">{label}</div>
    </div>
  );
}
