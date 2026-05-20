export default function Footer() {
  return (
    <footer className="mt-12 border-t border-[#dbe4f0] bg-white">
      <div className="shell flex flex-wrap items-center justify-between gap-3 py-6 text-sm font-semibold text-[#52647f]">
        <span className="font-black text-[#10213f]">PDFCraft</span>
        <div className="flex gap-4">
          <a href="#">Terms</a>
          <a href="#">Privacy</a>
          <a href="#">Contact</a>
        </div>
      </div>
    </footer>
  );
}
