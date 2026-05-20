import { createFileRoute, Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { FileText, Sparkles, Clock, ArrowRight } from "lucide-react";

export const Route = createFileRoute("/")({ component: Landing });

function Landing() {
  return (
    <div>
      <section className="bg-gradient-to-b from-white to-slate-100 border-b border-slate-200">
        <div className="max-w-5xl mx-auto px-6 py-20 lg:py-28 text-center">
          <span className="inline-block px-3 py-1 mb-6 text-xs font-medium tracking-wide rounded-full bg-indigo-50 text-indigo-700 border border-indigo-100">
            PDFCRAFT
          </span>
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight text-slate-900">
            Create Professional PDFs Instantly
          </h1>
          <p className="mt-6 max-w-2xl mx-auto text-lg text-slate-600">
            Turn your text into clean, downloadable PDFs in seconds. Start with 2 free PDF generations. Sign in when you need more.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link to="/generate">
              <Button size="lg" className="bg-indigo-600 hover:bg-indigo-700 text-white">
                Generate Your First PDF <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
            <Link to="/usage">
              <Button size="lg" variant="secondary">View my usage</Button>
            </Link>
          </div>
          <p className="mt-6 text-sm text-slate-500">
            You can generate <span className="font-semibold text-slate-700">2 PDFs for free</span>.
          </p>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 py-16 grid md:grid-cols-3 gap-5">
        {[
          { icon: Sparkles, t: "Fast PDF Creation", d: "Paste your content, add a title, and generate a clean PDF instantly." },
          { icon: FileText, t: "Free Starter Access", d: "Create your first 2 PDFs for free." },
          { icon: Clock, t: "Simple Document History", d: "View your recently generated PDFs in one place." },
        ].map((f) => (
          <Card key={f.t} className="p-6 bg-white border-slate-200 shadow-sm">
            <f.icon className="h-7 w-7 text-indigo-600 mb-4" />
            <h3 className="font-semibold text-slate-900">{f.t}</h3>
            <p className="mt-2 text-sm text-slate-600">{f.d}</p>
          </Card>
        ))}
      </section>
    </div>
  );
}
