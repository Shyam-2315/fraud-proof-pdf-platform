import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../api/client";
import { generatePdf, getVisitorStatus, identifyVisitor, type GeneratePdfResponse, type VisitorStatus } from "../api/userApi";
import ErrorState from "../components/ErrorState";
import Footer from "../components/Footer";
import LoadingState from "../components/LoadingState";
import Navbar from "../components/Navbar";
import PdfForm, { type PdfFormValues } from "../components/PdfForm";
import UsageCard from "../components/UsageCard";

export default function GeneratePage() {
  const [status, setStatus] = useState<VisitorStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function refreshStatus() {
    const nextStatus = await getVisitorStatus();
    setStatus(nextStatus);
  }

  useEffect(() => {
    async function load() {
      try {
        await identifyVisitor();
        await refreshStatus();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load usage.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function submit(values: PdfFormValues) {
    setError("");
    setMessage("");
    try {
      const result = await generatePdf(values);
      setMessage(result.message || "PDF generated successfully.");
      await refreshStatus();
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        const body = err.body as Partial<GeneratePdfResponse>;
        setMessage("");
        setError(body.message || "Free limit reached. Please log in to continue.");
        await refreshStatus();
        return;
      }
      setError(err instanceof Error ? err.message : "PDF generation failed.");
    }
  }

  return (
    <div>
      <Navbar />
      <main className="shell py-8">
        <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
          <div className="space-y-4">
            {message ? <div className="rounded-lg border border-[#b8e2c8] bg-[#effaf3] p-4 text-sm font-black text-[#17633a]">{message}</div> : null}
            {error ? (
              <div className="space-y-3">
                <ErrorState message={error} />
                {status?.requires_login ? (
                  <div className="panel p-5">
                    <p className="mb-4 text-sm font-bold text-[#52647f]">
                      Create an account to unlock more PDF generations.
                    </p>
                    <Link className="btn-primary" to="/login">Login / Signup</Link>
                  </div>
                ) : null}
                {error.includes("Monthly PDF limit") ? (
                  <div className="panel p-5">
                    <p className="mb-4 text-sm font-bold text-[#52647f]">
                      Choose a higher plan to keep generating PDFs this month.
                    </p>
                    <Link className="btn-primary" to="/pricing">View pricing</Link>
                  </div>
                ) : null}
              </div>
            ) : null}
            <PdfForm disabled={Boolean(status?.requires_login)} onSubmit={submit} />
          </div>
          <aside>{loading ? <LoadingState label="Loading usage..." /> : <UsageCard status={status} />}</aside>
        </div>
      </main>
      <Footer />
    </div>
  );
}
