export default function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-[#f0b6b6] bg-[#fff1f1] p-4 text-sm font-bold text-[#8b1e1e]">
      {message}
    </div>
  );
}
