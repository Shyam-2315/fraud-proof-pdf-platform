import { createFileRoute, Outlet, useRouterState } from "@tanstack/react-router";
import { AdminProtectedLayout } from "@/components/admin/AdminLayout";

export const Route = createFileRoute("/admin")({
  component: AdminRoot,
});

function AdminRoot() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  // The login page is rendered without the protected layout.
  if (pathname === "/admin/login") {
    return <Outlet />;
  }
  return <AdminProtectedLayout />;
}
