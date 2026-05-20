import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../api/client";
import { API_BASE_URL, getAccessToken } from "../api/client";
import { generatePdf, getVisitorStatus, identifyVisitor, sendBehaviorEvent, type GeneratePdfResponse, type VisitorStatus } from "../api/userApi";
import ErrorState from "../components/ErrorState";
import Footer from "../components/Footer";
import LoadingState from "../components/LoadingState";
import Navbar from "../components/Navbar";
import PdfForm, { type PdfFormValues } from "../components/PdfForm";
import UsageCard from "../components/UsageCard";
import { getIdentityHeaders } from "../utils/visitorIdentity";

export default function GeneratePage() {
  const [status, setStatus] = useState<VisitorStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [lastPdf, setLastPdf] = useState<{ pdf_id: string; file_name?: string } | null>(null);
  const [showLoginPrompt, setShowLoginPrompt] = useState(false);
  const [generating, setGenerating] = useState(false);

  async function refreshStatus() {
    const nextStatus = await getVisitorStatus();
    setStatus(nextStatus);
  }

  useEffect(() => {
    async function load() {
      try {
        await identifyVisitor();
        await sendBehaviorEvent("PAGE_VIEW", { page: "generate" });
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
    if (generating) return;
    setError("");
    setMessage("");
    setLastPdf(null);
    setShowLoginPrompt(false);
    setGenerating(true);
    try {
      const result = await generatePdf(values);
      await sendBehaviorEvent("PDF_GENERATED", { pdf_id: result.pdf_id, content: values.content });
      setMessage(result.message || "PDF generated successfully.");
      if (result.pdf_id) setLastPdf({ pdf_id: result.pdf_id, file_name: result.file_name });
      await refreshStatus();
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        const body = err.body as Partial<GeneratePdfResponse>;
        await sendBehaviorEvent("LIMIT_REACHED", { status: err.status });
        setMessage("");
        setError(body.message || "Free limit reached. Please log in to continue.");
        if (body.requires_login) setShowLoginPrompt(true);
        await refreshStatus();
        return;
      }
      setError(err instanceof Error ? err.message : "PDF generation failed.");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div>
      <Navbar />
      <main className="shell py-8">
        <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
          <div className="space-y-4">
            {lastPdf ? (
              <section className="rounded-lg border border-[#b8e2c8] bg-[#effaf3] p-5">
                <h2 className="text-xl font-black text-[#10213f]">Your PDF is ready.</h2>
                <p className="mt-2 text-sm font-bold text-[#17633a]">{message || "PDF generated successfully."}</p>
                <div className="mt-4 flex flex-wrap gap-3">
                  <button className="btn-primary" type="button" onClick={() => downloadPdf(lastPdf.pdf_id, lastPdf.file_name)}>
                    Download PDF
                  </button>
                  <Link className="btn-secondary" to="/history">
                    View My PDFs
                  </Link>
                </div>
              </section>
            ) : null}
            {error ? (
              <div className="space-y-3">
                <ErrorState message={error} />
                {showLoginPrompt ? (
                  <div className="panel p-5">
                    <p className="mb-4 text-sm font-bold text-[#52647f]">
                      Free limit reached. Please log in to continue.
                    </p>
                    <div className="flex flex-wrap gap-3">
                      <Link className="btn-primary" state={{ from: "/generate" }} to="/login">Login</Link>
                      <Link className="btn-secondary" state={{ from: "/generate" }} to="/signup">Sign Up</Link>
                    </div>
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
            <PdfForm disabled={generating} onSubmit={submit} />
          </div>
          <aside>{loading ? <LoadingState label="Loading usage..." /> : <UsageCard status={status} />}</aside>
        </div>
      </main>
      <Footer />
      {showLoginPrompt ? (
        <div className="fixed inset-0 z-50 grid place-items-center bg-[#101827]/60 px-4">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h2 className="text-xl font-black text-[#10213f]">Log in to continue</h2>
            <p className="mt-2 text-sm font-bold text-[#52647f]">
              Free limit reached. Please log in to continue.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Link className="btn-primary" state={{ from: "/generate" }} to="/login">Login</Link>
              <Link className="btn-secondary" state={{ from: "/generate" }} to="/signup">Sign Up</Link>
              <button className="btn-secondary" type="button" onClick={() => setShowLoginPrompt(false)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

async function downloadPdf(pdfId: string, fileName?: string) {
  const headers = new Headers(await getIdentityHeaders());
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE_URL}/api/pdf/download/${pdfId}`, {
    headers,
    credentials: "include",
  });
  if (!response.ok) return;
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName || `${pdfId}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
