import { Brain, Play } from "lucide-react";
import { useEffect, useState } from "react";
import { getActiveMLModel, getFraudSummary, trainMLModel, type FraudSummary } from "../api/adminApi";
import AdminNavbar from "../components/AdminNavbar";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";
import StatCard from "../components/StatCard";

export default function AdminMLEnginePage() {
  const [active, setActive] = useState<Record<string, unknown> | null>(null);
  const [summary, setSummary] = useState<FraudSummary | null>(null);
  const [demo, setDemo] = useState(true);
  const [autoActivate, setAutoActivate] = useState(false);
  const [training, setTraining] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const [activeResult, summaryResult] = await Promise.all([getActiveMLModel(), getFraudSummary()]);
      setActive(activeResult.active_model);
      setSummary(summaryResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load ML engine.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  async function train() {
    setTraining(true);
    setError("");
    try {
      const response = await trainMLModel({
        demo,
        synthetic_csv: demo ? "data/synthetic_fraud_dataset.csv" : undefined,
        auto_activate: autoActivate,
      });
      setResult(response);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Training failed.");
    } finally {
      setTraining(false);
    }
  }

  return (
    <div>
      <AdminNavbar />
      <main className="shell py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-black text-[#10213f]">ML Engine</h1>
          <p className="mt-2 text-sm font-semibold text-[#52647f]">Train and inspect internal fraud models.</p>
        </div>
        {loading ? <LoadingState label="Loading ML engine..." /> : null}
        {error ? <ErrorState message={error} /> : null}
        <div className="mb-6 grid gap-4 md:grid-cols-3">
          <StatCard label="Active Version" value={String(active?.version || "none")} icon={Brain} />
          <StatCard label="Training Events" value={summary?.training_events_collected || 0} icon={Brain} />
          <StatCard label="ML Decisions Today" value={summary?.ml_decisions_today || 0} icon={Brain} />
        </div>
        {!loading && !active?.version ? (
          <section className="mb-6 panel p-5 text-sm font-bold text-[#52647f]">
            No active model is configured. The rule engine fallback remains active.
          </section>
        ) : null}
        <section className="panel p-5">
          <h2 className="mb-4 text-xl font-black text-[#10213f]">Train New Model</h2>
          <div className="mb-4 flex flex-wrap gap-4">
            <label className="inline-flex items-center gap-2 text-sm font-bold text-[#21324e]">
              <input type="checkbox" checked={demo} onChange={(event) => setDemo(event.target.checked)} />
              Demo training data
            </label>
            <label className="inline-flex items-center gap-2 text-sm font-bold text-[#21324e]">
              <input type="checkbox" checked={autoActivate} onChange={(event) => setAutoActivate(event.target.checked)} />
              Auto activate
            </label>
          </div>
          <button className="btn-primary" type="button" disabled={training} onClick={train}>
            <Play size={18} />
            {training ? "Training..." : "Train New Model"}
          </button>
          {result ? (
            <pre className="mt-5 max-h-96 overflow-auto rounded-lg bg-[#101827] p-4 text-xs text-[#dce7f7]">
              {JSON.stringify(result, null, 2)}
            </pre>
          ) : null}
        </section>
      </main>
    </div>
  );
}
