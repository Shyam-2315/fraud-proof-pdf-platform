import { Filter } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { getFraudEvents, type FraudEvent } from "../api/adminApi";
import AdminNavbar from "../components/AdminNavbar";
import ErrorState from "../components/ErrorState";
import EventTable from "../components/EventTable";
import LoadingState from "../components/LoadingState";

export default function AdminEventsPage() {
  const [events, setEvents] = useState<FraudEvent[]>([]);
  const [severity, setSeverity] = useState("");
  const [eventType, setEventType] = useState("");
  const [allowed, setAllowed] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function load() {
    setLoading(true);
    setError("");
    try {
      const result = await getFraudEvents({
        severity,
        event_type: eventType,
        allowed: allowed === "" ? undefined : allowed === "true",
      });
      setEvents(result.items);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        navigate("/admin/login", { replace: true, state: { message: err.status === 401 ? "Admin API key required" : "Invalid admin API key" } });
        return;
      }
      setError(err instanceof Error ? err.message : "Unable to load fraud events.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div>
      <AdminNavbar />
      <main className="shell py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-black text-[#10213f]">Fraud Events</h1>
          <p className="mt-2 text-sm font-semibold text-[#52647f]">Newest internal monitoring events first.</p>
        </div>
        <section className="panel mb-5 grid gap-3 p-4 md:grid-cols-[180px_1fr_180px_auto]">
          <select className="field" value={severity} onChange={(event) => setSeverity(event.target.value)}>
            <option value="">All severities</option>
            <option value="LOW">LOW</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="HIGH">HIGH</option>
            <option value="CRITICAL">CRITICAL</option>
          </select>
          <input className="field" value={eventType} onChange={(event) => setEventType(event.target.value)} placeholder="Event type" />
          <select className="field" value={allowed} onChange={(event) => setAllowed(event.target.value)}>
            <option value="">All outcomes</option>
            <option value="true">Allowed</option>
            <option value="false">Blocked</option>
          </select>
          <button className="btn-primary" onClick={load}>
            <Filter size={18} />
            Apply
          </button>
        </section>
        {loading ? <LoadingState label="Loading fraud events..." /> : null}
        {error ? <ErrorState message={error} /> : null}
        {!loading && !error ? <EventTable events={events} /> : null}
      </main>
    </div>
  );
}
