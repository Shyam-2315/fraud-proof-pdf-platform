import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { getVisitorInvestigation, type VisitorInvestigation } from "../api/adminApi";
import AdminNavbar from "../components/AdminNavbar";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";

function JsonBlock({ value }: { value: unknown }) {
  return (
    <pre className="max-h-96 overflow-auto rounded-lg bg-[#101827] p-4 text-xs text-[#dce7f7]">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

export default function AdminVisitorInvestigationPage() {
  const { visitorId = "" } = useParams();
  const [data, setData] = useState<VisitorInvestigation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    async function load() {
      try {
        setData(await getVisitorInvestigation(visitorId));
      } catch (err) {
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          navigate("/admin/login", { replace: true, state: { message: err.status === 401 ? "Admin API key required" : "Invalid admin API key" } });
          return;
        }
        setError(err instanceof Error ? err.message : "Unable to load investigation.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [visitorId]);

  return (
    <div>
      <AdminNavbar />
      <main className="shell py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-black text-[#10213f]">Visitor Investigation</h1>
          <p className="mt-2 font-mono text-sm text-[#52647f]">{visitorId}</p>
        </div>
        {loading ? <LoadingState label="Loading investigation..." /> : null}
        {error ? <ErrorState message={error} /> : null}
        {data ? (
          <div className="grid gap-6">
            <section className="panel p-5">
              <h2 className="mb-4 text-xl font-black text-[#10213f]">Visitor profile</h2>
              <JsonBlock value={data.visitor} />
            </section>
            <section className="grid gap-4 md:grid-cols-2">
              <div className="panel p-5">
                <h2 className="mb-3 text-xl font-black text-[#10213f]">Generated PDFs by visitor</h2>
                <JsonBlock value={data.generated_pdfs} />
              </div>
              <div className="panel p-5">
                <h2 className="mb-3 text-xl font-black text-[#10213f]">Fraud events by visitor</h2>
                <JsonBlock value={data.fraud_events} />
              </div>
            </section>
            <section className="panel p-5">
              <h2 className="mb-4 text-xl font-black text-[#10213f]">Timeline</h2>
              <div className="space-y-3">
                {data.timeline.map((item) => (
                  <div key={item.id} className="rounded-lg border border-[#d8e1ee] p-4">
                    <div className="flex flex-wrap justify-between gap-2">
                      <span className="font-black text-[#10213f]">{item.title}</span>
                      <span className="text-sm font-bold text-[#52647f]">{new Date(item.created_at).toLocaleString()}</span>
                    </div>
                    <div className="mt-2 text-xs font-bold uppercase text-[#1459d9]">{item.item_type}</div>
                    <JsonBlock value={item.metadata} />
                  </div>
                ))}
              </div>
            </section>
          </div>
        ) : null}
      </main>
    </div>
  );
}
