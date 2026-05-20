import { ArrowRight, Clock, FileText, History } from "lucide-react";
import { Link } from "react-router-dom";
import Footer from "../components/Footer";
import Navbar from "../components/Navbar";

export default function LandingPage() {
  return (
    <div>
      <Navbar />
      <main>
        <section className="bg-[#f6f8fb] py-16 sm:py-20">
          <div className="shell grid gap-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
            <div>
              <p className="mb-3 text-sm font-black uppercase text-[#1459d9]">PDFCraft</p>
              <h1 className="max-w-3xl text-4xl font-black leading-tight text-[#10213f] sm:text-5xl">
                Create Professional PDFs Instantly
              </h1>
              <p className="mt-5 max-w-2xl text-xl font-semibold text-[#3c4e68]">
                Turn your text into clean, downloadable PDFs in seconds.
              </p>
              <p className="mt-4 max-w-2xl text-base font-semibold text-[#52647f]">
                Start with 2 free PDF generations. Sign in when you need more.
              </p>
              <Link className="btn-primary mt-8" to="/generate">
                Generate Your First PDF
                <ArrowRight size={18} />
              </Link>
            </div>
            <div className="panel bg-white p-6">
              <div className="rounded-lg border border-[#d8e1ee] bg-[#fbfcff] p-5">
                <div className="mb-5 h-4 w-52 rounded bg-[#d7e3f5]" />
                <div className="space-y-3">
                  <div className="h-3 rounded bg-[#e4ebf5]" />
                  <div className="h-3 rounded bg-[#e4ebf5]" />
                  <div className="h-3 w-4/5 rounded bg-[#e4ebf5]" />
                </div>
                <div className="mt-8 grid gap-3 sm:grid-cols-2">
                  <div className="h-20 rounded-lg bg-[#eaf1ff]" />
                  <div className="h-20 rounded-lg bg-[#e9f7ef]" />
                </div>
              </div>
            </div>
          </div>
        </section>
        <section className="border-t border-[#dbe4f0] bg-white py-12">
          <div className="shell grid gap-4 md:grid-cols-3">
            <article className="panel p-5">
              <FileText className="mb-4 text-[#1459d9]" size={26} />
              <h2 className="text-lg font-black text-[#10213f]">Fast PDF Creation</h2>
              <p className="mt-2 text-sm font-semibold text-[#52647f]">
                Paste your content, add a title, and generate a clean PDF instantly.
              </p>
            </article>
            <article className="panel p-5">
              <Clock className="mb-4 text-[#17633a]" size={26} />
              <h2 className="text-lg font-black text-[#10213f]">Free Starter Access</h2>
              <p className="mt-2 text-sm font-semibold text-[#52647f]">
                Create your first 2 PDFs for free.
              </p>
            </article>
            <article className="panel p-5">
              <History className="mb-4 text-[#7c4d00]" size={26} />
              <h2 className="text-lg font-black text-[#10213f]">Simple Document History</h2>
              <p className="mt-2 text-sm font-semibold text-[#52647f]">
                View your recently generated PDFs in one place.
              </p>
            </article>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
