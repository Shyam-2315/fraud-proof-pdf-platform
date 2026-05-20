import { Navigate, Outlet, useLocation } from "react-router-dom";
import { getAdminAccessToken, getAdminKey } from "../api/client";

export default function AdminProtectedRoute() {
  const location = useLocation();
  if (!getAdminKey() && !getAdminAccessToken()) {
    return <Navigate to="/admin/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}
