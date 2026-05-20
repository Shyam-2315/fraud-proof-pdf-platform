import { useEffect, useState } from "react";
import { getMyPdfHistory, identifyVisitor, type PdfHistory } from "../api/userApi";
import ErrorState from "../components/ErrorState";
import Footer from "../components/Footer";
import LoadingState from "../components/LoadingState";
import Navbar from "../components/Navbar";
import PdfHistoryTable from "../components/PdfHistoryTable";

export default function HistoryPage() {
  const [history, setHistory] = useState<PdfHistory | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        await identifyVisitor();
        setHistory(await getMyPdfHistory());
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load PDFs.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div>
      <Navbar />
      <main className="shell py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-black text-[#10213f]">My PDFs</h1>
          <p className="mt-2 text-sm font-semibold text-[#52647f]">Your recently generated documents.</p>
        </div>
        {loading ? <LoadingState label="Loading PDFs..." /> : null}
        {error ? <ErrorState message={error} /> : null}
        {!loading && !error ? <PdfHistoryTable items={history?.items || []} /> : null}
      </main>
      <Footer />
    </div>
  );
}
