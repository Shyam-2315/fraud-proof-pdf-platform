import { CheckCircle2, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { activateMLModel, getMLModels, rejectMLModel, type MLModelVersion } from "../api/adminApi";
import AdminNavbar from "../components/AdminNavbar";
import ErrorState from "../components/ErrorState";
import LoadingState from "../components/LoadingState";

export default function AdminMLModelsPage() {
  const [models, setModels] = useState<MLModelVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    try {
      setModels((await getMLModels()).items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load model versions.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  async function act(id: string, action: "activate" | "reject") {
    if (action === "activate") await activateMLModel(id);
    else await rejectMLModel(id);
    await load();
  }

  return (
    <div>
      <AdminNavbar />
      <main className="shell py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-black text-[#10213f]">Model Versions</h1>
          <p className="mt-2 text-sm font-semibold text-[#52647f]">Review, activate, or reject internal ML candidates.</p>
        </div>
        {loading ? <LoadingState label="Loading models..." /> : null}
        {error ? <ErrorState message={error} /> : null}
        {!loading && !error && models.length === 0 ? (
          <section className="panel p-6 text-sm font-bold text-[#52647f]">
            No model versions have been trained yet.
          </section>
        ) : null}
        {!loading && !error && models.length > 0 ? (
          <div className="panel table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Version</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Events</th>
                  <th>Positive</th>
                  <th>Negative</th>
                  <th>Precision</th>
                  <th>Recall</th>
                  <th>F1</th>
                  <th>ROC AUC</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {models.map((model) => (
                  <tr key={model.id}>
                    <td className="font-mono text-xs">{model.version}</td>
                    <td>{model.model_type}</td>
                    <td>{model.status}</td>
                    <td>{model.trained_on_event_count}</td>
                    <td>{model.positive_label_count}</td>
                    <td>{model.negative_label_count}</td>
                    <td>{metric(model, "precision")}</td>
                    <td>{metric(model, "recall")}</td>
                    <td>{metric(model, "f1_score")}</td>
                    <td>{metric(model, "roc_auc")}</td>
                    <td>{new Date(model.created_at).toLocaleString()}</td>
                    <td>
                      <div className="flex flex-wrap gap-2">
                        <button className="btn-secondary py-2" onClick={() => act(model.id, "activate")}>
                          <CheckCircle2 size={16} /> Activate
                        </button>
                        <button className="btn-secondary py-2" onClick={() => act(model.id, "reject")}>
                          <XCircle size={16} /> Reject
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </main>
    </div>
  );
}

function metric(model: MLModelVersion, key: string) {
  const value = model.metrics?.[key];
  return typeof value === "number" ? value.toFixed(3) : "-";
}
