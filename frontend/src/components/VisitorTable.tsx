import { Search } from "lucide-react";
import { Link } from "react-router-dom";
import type { AdminVisitor } from "../api/adminApi";

export default function VisitorTable({ visitors }: { visitors: AdminVisitor[] }) {
  return (
    <div className="panel table-wrap">
      <table>
        <thead>
          <tr>
            <th>Visitor</th>
            <th>Used</th>
            <th>Remaining</th>
            <th>Risk score</th>
            <th>Risk level</th>
            <th>Blocked</th>
            <th>Reason</th>
            <th>Local IDs</th>
            <th>Sessions</th>
            <th>Fingerprints</th>
            <th>IPs</th>
            <th>User agents</th>
            <th>First seen</th>
            <th>Last seen</th>
            <th>Investigation</th>
          </tr>
        </thead>
        <tbody>
          {visitors.map((visitor) => (
            <tr key={visitor.visitor_id}>
              <td className="font-mono text-xs">{visitor.visitor_id}</td>
              <td>{visitor.free_usage_count}</td>
              <td>{visitor.remaining_free_uses}</td>
              <td>{visitor.risk_score}</td>
              <td>{visitor.risk_level}</td>
              <td>{visitor.is_blocked ? "Yes" : "No"}</td>
              <td>{visitor.block_reason || "-"}</td>
              <td>{visitor.local_storage_id_count}</td>
              <td>{visitor.session_id_count}</td>
              <td>{visitor.fingerprint_hash_count}</td>
              <td>{visitor.ip_address_count}</td>
              <td>{visitor.user_agent_count}</td>
              <td>{new Date(visitor.first_seen_at).toLocaleString()}</td>
              <td>{new Date(visitor.last_seen_at).toLocaleString()}</td>
              <td>
                <Link className="btn-secondary py-2" to={`/admin/visitor/${encodeURIComponent(visitor.visitor_id)}`}>
                  <Search size={16} />
                  View
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
