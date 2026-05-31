import { adminRequest } from "./client";

export type AdminMonitoringResponse = {
  total_users: number;
  total_anonymous_visitors: number;
  total_pdfs_generated: number;
  pdfs_generated_today: number;
  blocked_visitors: number;
  fraud_decisions_count: number;
  mongodb_health: string;
  redis_health: string;
  storage_health: string;
  backend_readiness_status: string;
  checks: Record<string, boolean | string>;
};

export type AdminRequestLogItem = {
  request_id: string;
  method: string;
  path: string;
  status_code: number;
  duration_ms: number;
  client_ip?: string | null;
  block_reason?: string | null;
  fraud_score?: number | null;
  created_at: string;
};

export type AdminRequestLogListResponse = {
  total: number;
  limit: number;
  offset: number;
  items: AdminRequestLogItem[];
};

export type AdminFraudDecisionItem = {
  id: string;
  visitor_id?: string | null;
  user_id?: string | null;
  ip_address?: string | null;
  fingerprint_hash?: string | null;
  risk_score: number;
  risk_level: string;
  decision: string;
  action_type?: string | null;
  reason?: string | null;
  created_at: string;
};

export type AdminFraudDecisionListResponse = {
  total: number;
  limit: number;
  offset: number;
  items: AdminFraudDecisionItem[];
  decisions?: AdminFraudDecisionItem[];
};

export type AdminUserManagementItem = {
  user_id: string;
  email: string;
  full_name?: string | null;
  role: string;
  plan: string;
  is_active: boolean;
  is_verified: boolean;
  email_verified: boolean;
  used: number;
  limit: number;
  remaining: number;
  month_key: string;
  billing_period_start: string;
  billing_period_end: string;
  linked_visitor_count: number;
  created_at: string;
  last_login_at?: string | null;
};

export type AdminUserManagementListResponse = {
  total: number;
  limit: number;
  offset: number;
  items: AdminUserManagementItem[];
};

function query(filters?: Record<string, string | number | boolean | undefined | null>) {
  if (!filters) return "";
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  }
  const text = params.toString();
  return text ? `?${text}` : "";
}

export const adminApi = {
  getMonitoring: () => adminRequest<AdminMonitoringResponse>("/api/admin/monitoring"),
  getRequestLogs: (filters?: Record<string, string | number | boolean | undefined>) =>
    adminRequest<AdminRequestLogListResponse>(`/api/admin/logs${query(filters)}`),
  getAdminUsers: (filters?: Record<string, string | number | boolean | undefined>) =>
    adminRequest<AdminUserManagementListResponse>(`/api/admin/users${query(filters)}`),
  blockUser: (userId: string) =>
    adminRequest<{ success: boolean; user: AdminUserManagementItem }>(
      `/api/admin/users/${encodeURIComponent(userId)}/block`,
      { method: "POST" },
    ),
  unblockUser: (userId: string) =>
    adminRequest<{ success: boolean; user: AdminUserManagementItem }>(
      `/api/admin/users/${encodeURIComponent(userId)}/unblock`,
      { method: "POST" },
    ),
  getFraudSummary: () => adminRequest<any>("/api/admin/fraud/summary"),
  getFraudEvents: (filters?: Record<string, string | number | boolean | undefined>) =>
    adminRequest<any>(`/api/admin/fraud/events${query(filters)}`),
  getFraudVisitors: () => adminRequest<any>("/api/admin/fraud/visitors"),
  getVisitorInvestigation: (visitorId: string) =>
    adminRequest<any>(`/api/admin/fraud/visitor/${encodeURIComponent(visitorId)}`),
  getFraudDecisions: (
    filters?: string | Record<string, string | number | boolean | undefined>,
  ) => {
    const values = typeof filters === "string" ? { visitor_id: filters } : filters;
    return adminRequest<AdminFraudDecisionListResponse>(
      `/api/admin/fraud/decisions${query(values)}`,
    );
  },
  getFraudFeatures: (visitorId: string) =>
    adminRequest<any>(`/api/admin/fraud/features/${encodeURIComponent(visitorId)}`),
  getIdentityLinks: (visitorId: string) =>
    adminRequest<any>(`/api/admin/fraud/identity-links/${encodeURIComponent(visitorId)}`),
  labelVisitor: (payload: { visitor_id: string; label: number; notes?: string }) =>
    adminRequest<any>("/api/admin/fraud/label", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getAllPdfs: () => adminRequest<any>("/api/admin/pdfs"),
  getAuditLogs: () => adminRequest<any>("/api/admin/audit-logs"),
  getMLModels: () => adminRequest<any>("/api/admin/ml/models"),
  getActiveMLModel: () => adminRequest<any>("/api/admin/ml/models/active"),
  trainMLModel: (payload: { demo?: boolean; auto_activate?: boolean }) =>
    adminRequest<any>("/api/admin/ml/train", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  activateMLModel: (modelVersionId: string) =>
    adminRequest<any>(`/api/admin/ml/models/${encodeURIComponent(modelVersionId)}/activate`, {
      method: "POST",
    }),
  rejectMLModel: (modelVersionId: string) =>
    adminRequest<any>(`/api/admin/ml/models/${encodeURIComponent(modelVersionId)}/reject`, {
      method: "POST",
    }),
};
