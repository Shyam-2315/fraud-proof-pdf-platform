import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { extractError } from "@/api/client";
import { generatePdf, getVisitorStatus, type VisitorStatus } from "@/api/userApi";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import { AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";

export const Route = createFileRoute("/generate")({ component: GeneratePage });

function GeneratePage() {
  const [title, setTitle] = useState("Demo PDF");
  const [content, setContent] = useState("PDF content here");
  const [submitting, setSubmitting] = useState(false);
  const [status, setStatus] = useState<VisitorStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [blocked, setBlocked] = useState<string | null>(null);
  const [last, setLast] = useState<{ title: string; remaining: number } | null>(null);

  const refresh = async () => {
    try { setStatus(await getVisitorStatus()); } catch (e) { setError(extractError(e)); }
  };
  useEffect(() => { refresh(); }, []);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true); setError(null); setBlocked(null); setLast(null);
    try {
      const data = await generatePdf(title, content);
      setLast({ title: title, remaining: data.remaining_free_uses ?? 0 });
      toast.success(data.message || "PDF generated.");
      await refresh();
    } catch (err) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const e = err as any;
      const detail = e?.response?.data?.detail;
      if (e?.response?.status === 403 || detail?.reason === "FREE_LIMIT_REACHED") {
        setBlocked(detail?.message || "Free limit reached. Please log in to continue.");
      } else {
        setError(extractError(err));
      }
      await refresh();
    } finally {
      setSubmitting(false);
    }
  };

  const used = status?.free_usage_count ?? 0;
  const limit = status?.free_usage_limit ?? 2;
  const remaining = status?.remaining_free_uses ?? Math.max(0, limit - used);
  const pct = limit > 0 ? Math.min(100, (used / limit) * 100) : 0;

  return (
    <div className="max-w-5xl mx-auto px-6 py-10 grid lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        <Card className="p-6 bg-white border-slate-200 shadow-sm">
          <h1 className="text-2xl font-semibold text-slate-900">Generate PDF</h1>
          <p className="text-sm text-slate-600 mt-1">Fill in a title and content to create your PDF.</p>

          {blocked && (
            <Alert className="mt-4 border-red-200 bg-red-50 text-red-800">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Free limit reached. Please log in to continue.</AlertTitle>
              <AlertDescription className="flex flex-wrap items-center justify-between gap-3">
                <span>Create an account to unlock more PDF generations.</span>
                <div className="flex gap-2">
                  <Link to="/login"><Button size="sm" variant="outline">Sign in</Button></Link>
                  <Link to="/register"><Button size="sm" className="bg-red-600 hover:bg-red-700 text-white">Sign up</Button></Link>
                </div>
              </AlertDescription>
            </Alert>
          )}
          {error && (
            <Alert className="mt-4 border-amber-200 bg-amber-50 text-amber-800">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {last && (
            <Alert className="mt-4 border-emerald-200 bg-emerald-50 text-emerald-800">
              <CheckCircle2 className="h-4 w-4" />
              <AlertTitle>PDF generated successfully.</AlertTitle>
              <AlertDescription>
                <strong>{last.title}</strong> — {last.remaining} free PDF(s) remaining.
              </AlertDescription>
            </Alert>
          )}

          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <div>
              <Label htmlFor="title">PDF title</Label>
              <Input id="title" value={title} onChange={(e) => setTitle(e.target.value)} required />
            </div>
            <div>
              <Label htmlFor="content">Content</Label>
              <Textarea id="content" rows={8} value={content} onChange={(e) => setContent(e.target.value)} required />
            </div>
            <Button type="submit" disabled={submitting || status?.is_blocked} className="bg-indigo-600 hover:bg-indigo-700 text-white">
              {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Generate PDF
            </Button>
          </form>
        </Card>
      </div>

      <Card className="p-6 bg-white border-slate-200 shadow-sm h-fit">
        <h2 className="text-lg font-semibold text-slate-900">Free PDFs</h2>
        {!status ? (
          <p className="mt-4 text-sm text-slate-500">Loading…</p>
        ) : (
          <div className="mt-4 space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-slate-600">Free PDFs Used</span>
              <span className="font-medium text-slate-900">{used} / {limit}</span>
            </div>
            <Progress value={pct} />
            <div className="flex justify-between text-sm">
              <span className="text-slate-600">Remaining Free PDFs</span>
              <span className="font-medium text-slate-900">{remaining}</span>
            </div>
            {status.is_blocked && (
              <div className="mt-3 rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-800">
                Free limit reached. Please log in to continue.
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
