import type { FraudEvent } from "../api/adminApi";

function tone(value: string) {
  if (value === "CRITICAL" || value === "HIGH") return "bg-[#ffe9e9] text-[#9a1717]";
  if (value === "MEDIUM") return "bg-[#fff4d8] text-[#765000]";
  return "bg-[#e8f6ee] text-[#17633a]";
}

export default function EventTable({ events }: { events: FraudEvent[] }) {
  return (
    <div className="panel table-wrap">
      <table>
        <thead>
          <tr>
            <th>Created</th>
            <th>Visitor</th>
            <th>Event type</th>
            <th>Severity</th>
            <th>Allowed</th>
            <th>Reason</th>
            <th>Risk level</th>
            <th>IP address</th>
          </tr>
        </thead>
        <tbody>
          {events.map((event) => (
            <tr key={event.id}>
              <td>{new Date(event.created_at).toLocaleString()}</td>
              <td className="font-mono text-xs">{event.visitor_id || "-"}</td>
              <td>{event.event_type}</td>
              <td>
                <span className={`badge ${tone(event.severity)}`}>{event.severity}</span>
              </td>
              <td>
                <span className={`badge ${event.allowed ? "bg-[#e8f6ee] text-[#17633a]" : "bg-[#ffe9e9] text-[#9a1717]"}`}>
                  {event.allowed ? "ALLOWED" : "BLOCKED"}
                </span>
              </td>
              <td>{event.reason || "-"}</td>
              <td>{event.risk_level}</td>
              <td>{event.ip_address || "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
