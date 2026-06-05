import { type FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Combine, Download, FileText, Gauge, Image, Loader2, Lock, Scissors, Upload } from "lucide-react";
import { ApiError, apiUrl, getAccessToken } from "../api/client";
import {
  ensureVisitorIdentified,
  getVisitorStatusAfterIdentify,
  getVisitorStatusMessage,
  isVisitorLimitReached,
  isVisitorStatusBlocked,
  sendBehaviorEvent,
  textToPdf,
  uploadPdfTool,
  type GeneratePdfResponse,
  type VisitorStatus,
} from "../api/userApi";
import ErrorState from "../components/ErrorState";
import Footer from "../components/Footer";
import LoadingState from "../components/LoadingState";
import Navbar from "../components/Navbar";
import UsageCard from "../components/UsageCard";
import { useAuth } from "../context/AuthContext";
import { getIdentityHeaders } from "../utils/visitorIdentity";

type ToolId = "text" | "image" | "merge" | "split" | "compress" | "protect";

const tools: Array<{ id: ToolId; label: string; icon: typeof FileText }> = [
  { id: "text", label: "Text to PDF", icon: FileText },
  { id: "image", label: "Image to PDF", icon: Image },
  { id: "merge", label: "Merge PDFs", icon: Combine },
  { id: "split", label: "Split PDF", icon: Scissors },
  { id: "compress", label: "Compress PDF", icon: Gauge },
  { id: "protect", label: "Password protect PDF", icon: Lock },
];

export default function ToolsPage() {
  const [selectedTool, setSelectedTool] = useState<ToolId>("text");
  const [title, setTitle] = useState("New PDF");
  const [content, setContent] = useState("");
  const [pageRanges, setPageRanges] = useState("");
  const [password, setPassword] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [status, setStatus] = useState<VisitorStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<GeneratePdfResponse | null>(null);
  const { isAuthenticated } = useAuth();

  const selected = useMemo(() => tools.find((tool) => tool.id === selectedTool) || tools[0], [selectedTool]);
  const SelectedIcon = selected.icon;

  async function refreshStatus() {
    const nextStatus = await getVisitorStatusAfterIdentify();
    setStatus(nextStatus);
    return nextStatus;
  }

  useEffect(() => {
    async function load() {
      try {
        await sendBehaviorEvent("PAGE_VIEW", { page: "tools" });
        if (!isAuthenticated) {
          await ensureVisitorIdentified();
          await refreshStatus();
        }
      } catch {
        setError("We could not start your session. Please refresh and try again.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [isAuthenticated]);

  function switchTool(toolId: ToolId) {
    setSelectedTool(toolId);
    setResult(null);
    setError("");
    setFiles([]);
    setPageRanges("");
    setPassword("");
    setTitle(defaultTitle(toolId));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    if (!isAuthenticated && isVisitorStatusBlocked(status)) {
      setError(getVisitorStatusMessage(status));
      return;
    }
    setSubmitting(true);
    setError("");
    setResult(null);
    try {
      await ensureVisitorIdentified();
      const response = selectedTool === "text" ? await submitTextTool() : await submitUploadTool();
      setResult(response);
      if (!isAuthenticated) await refreshStatus();
    } catch (err) {
      if (err instanceof ApiError) {
        const nextStatus = isAuthenticated ? null : await refreshStatus().catch(() => null);
        if (nextStatus && isVisitorStatusBlocked(nextStatus)) {
          setError(getVisitorStatusMessage(nextStatus));
        } else {
          setError(getToolErrorMessage(err, err.body as Partial<GeneratePdfResponse>));
        }
      } else if (err instanceof Error && err.message) {
        setError(err.message);
      } else {
        setError("We could not process this PDF tool request. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  function submitTextTool() {
    return textToPdf({ title, content });
  }

  function submitUploadTool() {
    const formData = new FormData();
    formData.append("title", title);
    if (selectedTool === "split") formData.append("page_ranges", pageRanges);
    if (selectedTool === "protect") formData.append("password", password);

    if (selectedTool === "image" || selectedTool === "merge") {
      const minimum = selectedTool === "merge" ? 2 : 1;
      if (files.length < minimum) throw new Error(`Select at least ${minimum} file(s).`);
      files.forEach((file) => formData.append("files", file));
    } else {
      if (!files[0]) throw new Error("Select a PDF file.");
      formData.append("file", files[0]);
    }
    return uploadPdfTool(toolEndpoint(selectedTool), formData);
  }

  return (
    <div>
      <Navbar />
      <main className="shell py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-black text-[#10213f]">PDF tools</h1>
          <p className="mt-2 text-sm font-semibold text-[#52647f]">Create, combine, split, compress, and protect documents.</p>
        </div>
        <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
          <div className="space-y-4">
            <section className="panel p-3">
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {tools.map(({ id, label, icon: Icon }) => (
                  <button
                    key={id}
                    type="button"
                    className={`flex items-center gap-3 rounded-lg border px-3 py-3 text-left text-sm font-black ${
                      selectedTool === id
                        ? "border-[#1459d9] bg-[#eaf1ff] text-[#1459d9]"
                        : "border-[#d8e1ee] bg-white text-[#1b335d] hover:bg-[#f6f9fe]"
                    }`}
                    onClick={() => switchTool(id)}
                  >
                    <Icon size={18} />
                    {label}
                  </button>
                ))}
              </div>
            </section>

            {result?.pdf_id ? (
              <section className="rounded-lg border border-[#b8e2c8] bg-[#effaf3] p-5">
                <h2 className="text-xl font-black text-[#10213f]">Your PDF is ready.</h2>
                <p className="mt-2 text-sm font-bold text-[#17633a]">{result.message}</p>
                <button className="btn-primary mt-4" type="button" onClick={() => void downloadPdf(result)}>
                  <Download size={17} />
                  Download PDF
                </button>
              </section>
            ) : null}

            {error ? (
              <div className="space-y-3">
                <ErrorState message={error} />
                {isVisitorLimitReached(status) ? (
                  <div className="panel p-5">
                    <div className="flex flex-wrap gap-3">
                      <Link className="btn-primary" state={{ from: "/tools" }} to="/login">Login</Link>
                      <Link className="btn-secondary" state={{ from: "/tools" }} to="/signup">Sign Up</Link>
                    </div>
                  </div>
                ) : null}
                {error.includes("Monthly PDF limit") ? <Link className="btn-primary" to="/pricing">View pricing</Link> : null}
              </div>
            ) : null}

            <section className="panel p-5">
              <div className="mb-5 flex items-center gap-3">
                <SelectedIcon size={24} className="text-[#1459d9]" />
                <h2 className="text-xl font-black text-[#10213f]">{selected.label}</h2>
              </div>
              <form className="grid gap-4" onSubmit={submit}>
                <label className="grid gap-2 text-sm font-bold text-[#52647f]">
                  Title
                  <input className="field" maxLength={120} required value={title} onChange={(event) => setTitle(event.target.value)} />
                </label>

                {selectedTool === "text" ? (
                  <label className="grid gap-2 text-sm font-bold text-[#52647f]">
                    Text
                    <textarea
                      className="field min-h-56"
                      maxLength={20000}
                      required
                      value={content}
                      onChange={(event) => setContent(event.target.value)}
                    />
                  </label>
                ) : (
                  <label className="grid gap-2 text-sm font-bold text-[#52647f]">
                    Files
                    <input
                      className="field"
                      type="file"
                      accept={selectedTool === "image" ? "image/png,image/jpeg,image/webp" : "application/pdf"}
                      multiple={selectedTool === "image" || selectedTool === "merge"}
                      required
                      onChange={(event) => setFiles(Array.from(event.target.files || []))}
                    />
                  </label>
                )}

                {selectedTool === "split" ? (
                  <label className="grid gap-2 text-sm font-bold text-[#52647f]">
                    Pages
                    <input className="field" placeholder="1-3,5" value={pageRanges} onChange={(event) => setPageRanges(event.target.value)} />
                  </label>
                ) : null}

                {selectedTool === "protect" ? (
                  <label className="grid gap-2 text-sm font-bold text-[#52647f]">
                    Password
                    <input
                      className="field"
                      minLength={6}
                      maxLength={128}
                      required
                      type="password"
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                    />
                  </label>
                ) : null}

                <button
                  className="btn-primary w-full sm:w-auto"
                  disabled={submitting || (!isAuthenticated && isVisitorStatusBlocked(status))}
                  type="submit"
                >
                  {submitting ? <Loader2 size={17} className="animate-spin" /> : <Upload size={17} />}
                  {submitting ? "Processing..." : "Create PDF"}
                </button>
              </form>
            </section>
          </div>
          <aside>{loading ? <LoadingState label="Loading usage..." /> : <UsageCard status={status} showLoginCta={!isAuthenticated && isVisitorLimitReached(status)} />}</aside>
        </div>
      </main>
      <Footer />
    </div>
  );
}

function defaultTitle(toolId: ToolId) {
  const labels: Record<ToolId, string> = {
    text: "Text PDF",
    image: "Image PDF",
    merge: "Merged PDF",
    split: "Split PDF",
    compress: "Compressed PDF",
    protect: "Protected PDF",
  };
  return labels[toolId];
}

function toolEndpoint(toolId: ToolId) {
  const endpoints: Record<ToolId, string> = {
    text: "/api/pdf/tools/text-to-pdf",
    image: "/api/pdf/tools/image-to-pdf",
    merge: "/api/pdf/tools/merge",
    split: "/api/pdf/tools/split",
    compress: "/api/pdf/tools/compress",
    protect: "/api/pdf/tools/password-protect",
  };
  return endpoints[toolId];
}

function getToolErrorMessage(error: ApiError, body: Partial<GeneratePdfResponse>) {
  if (error.status === 429) return "Too many requests. Please wait a moment and try again.";
  if (body?.requires_login) return body.message || "Free limit reached. Please log in to continue.";
  if (body?.requires_upgrade) return body.message || "Monthly PDF limit reached. Please upgrade your plan to continue.";
  if (error.status === 400) return error.message || "Uploaded file is invalid.";
  if (error.status >= 500) return "We could not process this PDF tool request. Please try again.";
  return error.message || "We could not process this PDF tool request. Please try again.";
}

async function downloadPdf(result: GeneratePdfResponse) {
  if (!result.pdf_id) return;
  const headers = new Headers(await getIdentityHeaders());
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(apiUrl(result.download_url || `/api/pdf/download/${result.pdf_id}`), {
    headers,
    credentials: "include",
  });
  if (!response.ok) return;
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = result.file_name || `${result.pdf_id}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
