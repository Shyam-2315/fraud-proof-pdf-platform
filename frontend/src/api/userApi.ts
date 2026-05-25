import { customerRequest, identifyRequest } from "./client";

export type PublicConfig = {
  product_name: string;
  tagline: string;
  free_limit: number;
  login_required_message: string;
};

export type VisitorStatus = {
  visitor_id: string;
  free_usage_count: number;
  free_usage_limit: number;
  remaining_free_uses: number;
  is_blocked: boolean;
  message: string | null;
  requires_login?: boolean;
};

export type GeneratePdfResponse = {
  success: boolean;
  message: string;
  pdf_id?: string;
  title?: string;
  file_name?: string;
  free_limit?: number;
  free_usage_count?: number;
  free_usage_limit?: number;
  remaining_free_uses?: number;
  plan?: string;
  limit?: number;
  used?: number;
  remaining?: number;
  requires_login?: boolean;
  requires_upgrade?: boolean;
};

export type PdfHistoryItem = {
  pdf_id: string;
  title: string;
  file_name: string;
  created_at: string;
  download_url: string;
};

export type PdfHistory = {
  total: number;
  items: PdfHistoryItem[];
};

export function getPublicConfig() {
  return customerRequest<PublicConfig>("/api/public/config");
}

export function identifyVisitor() {
  return identifyRequest<{ success: boolean; visitor_id: string; message: string }>();
}

export function ensureVisitorIdentified() {
  return identifyVisitor();
}

export function getVisitorStatus() {
  return customerRequest<VisitorStatus>("/api/visitor/status");
}

export function generatePdf(payload: { title: string; content: string }) {
  return customerRequest<GeneratePdfResponse>("/api/pdf/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function sendBehaviorEvent(event_type: string, metadata: Record<string, unknown> = {}) {
  return customerRequest<{ success: boolean }>("/api/behavior/event", {
    method: "POST",
    body: JSON.stringify({ event_type, metadata }),
  }).catch(() => ({ success: false }));
}

export function getMyPdfHistory() {
  return customerRequest<PdfHistory>("/api/pdf/my-history");
}
