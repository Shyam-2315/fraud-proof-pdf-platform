import { Activity, BarChart3, Brain, ClipboardList, FileText, GitBranch, LogOut, Users } from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";
import { clearAdminAccessToken, clearAdminKey } from "../api/client";

const links = [
  { to: "/admin/dashboard", label: "Dashboard", icon: BarChart3 },
  { to: "/admin/events", label: "Events", icon: Activity },
  { to: "/admin/ml", label: "ML Engine", icon: Brain },
  { to: "/admin/ml/models", label: "Model Versions", icon: GitBranch },
  { to: "/admin/visitors", label: "Visitors", icon: Users },
  { to: "/admin/pdfs", label: "PDFs", icon: FileText },
  { to: "/admin/audit-logs", label: "Audit Logs", icon: ClipboardList },
];

export default function AdminNavbar() {
  const navigate = useNavigate();

  function logout() {
    clearAdminKey();
    clearAdminAccessToken();
    navigate("/admin/login");
  }

  return (
    <header className="border-b border-[#253048] bg-[#12192a] text-white">
      <div className="shell flex min-h-16 flex-wrap items-center justify-between gap-4 py-3">
        <NavLink to="/admin/dashboard" className="text-lg font-black">
          Fraud Proof PDF Platform
        </NavLink>
        <nav className="flex flex-wrap items-center gap-2">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-bold ${
                  isActive ? "bg-white text-[#12192a]" : "text-[#d8e1ef] hover:bg-[#1e2a44]"
                }`
              }
            >
              <Icon size={17} />
              {label}
            </NavLink>
          ))}
          <button className="btn-secondary border-[#4d5d7b] bg-[#1e2a44] text-white" onClick={logout}>
            <LogOut size={17} />
            Sign out
          </button>
        </nav>
      </div>
    </header>
  );
}
