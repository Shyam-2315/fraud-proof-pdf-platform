import { adminRequest } from "./client";

export type FraudSummary = {
  total_visitors: number;
  blocked_visitors: number;
  total_generated_pdfs: number;
  total_fraud_events: number;
  allowed_pdf_generations: number;
  blocked_pdf_generations: number;
  high_risk_visitors: number;
  medium_risk_visitors: number;
  low_risk_visitors: number;
};

export type FraudEvent = {
  id: string;
  visitor_id: string | null;
  event_type: string;
  severity: string;
  action: string;
  allowed: boolean;
  reason: string | null;
  risk_score: number;
  risk_level: string;
  fingerprint_hash: string | null;
  local_storage_id: string | null;
  session_id: string | null;
  cookie_id: string | null;
  ip_address: string | null;
  user_agent: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AdminVisitor = {
  visitor_id: string;
  free_usage_count: number;
  free_usage_limit: number;
  remaining_free_uses: number;
  risk_score: number;
  risk_level: string;
  is_blocked: boolean;
  block_reason: string | null;
  local_storage_id_count: number;
  session_id_count: number;
  fingerprint_hash_count: number;
  ip_address_count: number;
  user_agent_count: number;
  first_seen_at: string;
  last_seen_at: string;
};

export type AdminPdf = {
  pdf_id: string;
  visitor_id: string | null;
  title: string;
  file_name: string;
  file_path: string;
  generation_type: string;
  fingerprint_hash: string | null;
  ip_address: string | null;
  created_at: string;
};

export type TimelineItem = {
  id: string;
  item_type: string;
  title: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type VisitorInvestigation = {
  visitor: Record<string, unknown>;
  generated_pdfs: AdminPdf[];
  fraud_events: FraudEvent[];
  timeline: TimelineItem[];
};

export type AuditLog = {
  id: string;
  action: string;
  target_type: string;
  target_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

type ListResponse<T> = { total: number; limit: number; items: T[] };

function query(params: Record<string, string | boolean | undefined>) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") search.set(key, String(value));
  });
  const value = search.toString();
  return value ? `?${value}` : "";
}

export function getFraudSummary() {
  return adminRequest<FraudSummary>("/api/admin/fraud/summary");
}

export function getFraudEvents(filters: {
  severity?: string;
  event_type?: string;
  visitor_id?: string;
  allowed?: boolean;
} = {}) {
  return adminRequest<ListResponse<FraudEvent>>(
    `/api/admin/fraud/events${query(filters)}`,
  );
}

export function getFraudVisitors() {
  return adminRequest<ListResponse<AdminVisitor>>("/api/admin/fraud/visitors");
}

export function getVisitorInvestigation(visitorId: string) {
  return adminRequest<VisitorInvestigation>(
    `/api/admin/fraud/visitor/${encodeURIComponent(visitorId)}`,
  );
}

export function getAllPdfs() {
  return adminRequest<ListResponse<AdminPdf>>("/api/admin/pdfs");
}

export function getAuditLogs() {
  return adminRequest<ListResponse<AuditLog>>("/api/admin/audit-logs");
}
