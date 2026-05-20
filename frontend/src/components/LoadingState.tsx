export default function LoadingState({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="panel p-6 text-sm font-bold text-[#52647f]" role="status">
      {label}
    </div>
  );
}
