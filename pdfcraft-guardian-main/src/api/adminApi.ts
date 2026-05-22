import { adminRequest } from "./client";

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
  getFraudSummary: () => adminRequest<any>("/api/admin/fraud/summary"),
  getFraudEvents: (filters?: Record<string, string | number | boolean | undefined>) =>
    adminRequest<any>(`/api/admin/fraud/events${query(filters)}`),
  getFraudVisitors: () => adminRequest<any>("/api/admin/fraud/visitors"),
  getVisitorInvestigation: (visitorId: string) =>
    adminRequest<any>(`/api/admin/fraud/visitor/${encodeURIComponent(visitorId)}`),
  getFraudDecisions: (visitorId?: string) =>
    adminRequest<any>(`/api/admin/fraud/decisions${query({ visitor_id: visitorId })}`),
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
