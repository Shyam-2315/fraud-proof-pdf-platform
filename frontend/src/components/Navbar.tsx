import { BarChart3, CreditCard, FileText, History, Home, LogIn, LogOut, UserPlus, UserRound } from "lucide-react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const publicLinks = [
  { to: "/", label: "Home", icon: Home },
  { to: "/generate", label: "Generate", icon: FileText },
  { to: "/pricing", label: "Pricing", icon: CreditCard },
];

const accountLinks = [
  { to: "/history", label: "My PDFs", icon: History },
  { to: "/usage", label: "Usage", icon: BarChart3 },
];

export default function Navbar() {
  const { isAuthenticated, logout } = useAuth();
  const links = isAuthenticated ? [...publicLinks, ...accountLinks] : publicLinks;

  return (
    <header className="border-b border-[#dbe4f0] bg-white">
      <div className="shell flex min-h-16 flex-wrap items-center justify-between gap-4 py-3">
        <NavLink to="/" className="text-xl font-black text-[#10213f]">
          PDFCraft
        </NavLink>
        <nav className="flex flex-wrap items-center gap-2">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-bold ${
                  isActive
                    ? "bg-[#eaf1ff] text-[#1459d9]"
                    : "text-[#52647f] hover:bg-[#f1f5fb] hover:text-[#17345f]"
                }`
              }
            >
              <Icon size={17} />
              {label}
            </NavLink>
          ))}
          {isAuthenticated ? (
            <>
              <NavLink
                to="/account"
                className={({ isActive }) =>
                  `inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-bold ${
                    isActive
                      ? "bg-[#eaf1ff] text-[#1459d9]"
                      : "text-[#52647f] hover:bg-[#f1f5fb] hover:text-[#17345f]"
                  }`
                }
              >
                <UserRound size={17} />
                Account
              </NavLink>
              <button className="btn-secondary py-2" onClick={logout}>
                <LogOut size={17} />
                Logout
              </button>
            </>
          ) : (
            <>
              <NavLink className="btn-secondary py-2" to="/login">
                <LogIn size={17} />
                Login
              </NavLink>
              <NavLink className="btn-primary py-2" to="/signup">
                <UserPlus size={17} />
                Sign Up
              </NavLink>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
