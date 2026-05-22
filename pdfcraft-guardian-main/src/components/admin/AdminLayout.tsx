import { useEffect, useState } from "react";
import { Link, Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard,
  ShieldAlert,
  Users,
  FileText,
  Brain,
  GitBranch,
  ClipboardList,
  LogOut,
  Menu,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { clearAdminAuth, isAdminAuthenticated } from "@/lib/adminApi";
import { Toaster } from "@/components/ui/sonner";

const NAV = [
  { to: "/admin/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/admin/events", label: "Fraud Events", icon: ShieldAlert },
  { to: "/admin/visitors", label: "Visitors", icon: Users },
  { to: "/admin/pdfs", label: "All PDFs", icon: FileText },
  { to: "/admin/ml", label: "ML Engine", icon: Brain },
  { to: "/admin/ml/models", label: "Model Versions", icon: GitBranch },
  { to: "/admin/audit-logs", label: "Audit Logs", icon: ClipboardList },
] as const;

const PAGE_TITLES: Record<string, string> = {
  "/admin/dashboard": "Dashboard",
  "/admin/events": "Fraud Events",
  "/admin/visitors": "Visitors",
  "/admin/pdfs": "All PDFs",
  "/admin/ml": "ML Engine",
  "/admin/ml/models": "Model Versions",
  "/admin/audit-logs": "Audit Logs",
};

export function AdminProtectedLayout() {
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const [authChecked, setAuthChecked] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (!isAdminAuthenticated()) {
      navigate({ to: "/admin/login" });
    } else {
      setAuthChecked(true);
    }
  }, [navigate]);

  if (!authChecked) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-muted/30">
        <p className="text-sm text-muted-foreground">Checking admin session…</p>
      </div>
    );
  }

  const handleLogout = () => {
    clearAdminAuth();
    navigate({ to: "/admin/login" });
  };

  const title =
    PAGE_TITLES[pathname] ||
    (pathname.startsWith("/admin/visitor/") ? "Visitor Investigation" : "Admin");

  return (
    <div className="flex min-h-screen w-full bg-muted/30">
      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r bg-card transition-transform lg:static lg:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-16 items-center justify-between border-b px-6">
          <div>
            <div className="text-sm font-semibold leading-tight">Fraud Proof</div>
            <div className="text-xs text-muted-foreground">PDF Platform</div>
          </div>
          <button
            className="lg:hidden text-muted-foreground"
            onClick={() => setMobileOpen(false)}
            aria-label="Close menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {NAV.map((item) => {
            const Icon = item.icon;
            const active =
              pathname === item.to ||
              (item.to !== "/admin/dashboard" &&
                item.to !== "/admin/ml" &&
                pathname.startsWith(item.to + "/"));
            return (
              <Link
                key={item.to}
                to={item.to}
                onClick={() => setMobileOpen(false)}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-primary text-primary-foreground"
                    : "text-foreground/80 hover:bg-muted hover:text-foreground",
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t p-3">
          <Button variant="ghost" className="w-full justify-start" onClick={handleLogout}>
            <LogOut className="mr-2 h-4 w-4" /> Logout
          </Button>
        </div>
      </aside>

      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <div className="flex min-h-screen flex-1 flex-col lg:pl-0">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b bg-background/95 px-4 backdrop-blur lg:px-8">
          <div className="flex items-center gap-3">
            <button
              className="lg:hidden"
              onClick={() => setMobileOpen(true)}
              aria-label="Open menu"
            >
              <Menu className="h-5 w-5" />
            </button>
            <h1 className="text-lg font-semibold">{title}</h1>
          </div>
          <Button variant="outline" size="sm" onClick={handleLogout}>
            <LogOut className="mr-2 h-4 w-4" /> Sign out
          </Button>
        </header>
        <main className="flex-1 p-4 lg:p-8">
          <Outlet />
        </main>
      </div>
      <Toaster />
    </div>
  );
}
