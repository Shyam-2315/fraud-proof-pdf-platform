import { customerRequest, identifyRequest } from "./client";

export type PublicConfig = {
  product_name: string;
  tagline: string;
  free_limit: number;
  login_required_message: string;
};

export type VisitorStatus = {
  visitor_id: string;
  used: number;
  remaining: number;
  free_limit: number;
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

let publicConfigPromise: Promise<PublicConfig> | null = null;
let identifyPromise: Promise<{ success: boolean; visitor_id: string; message: string }> | null = null;
let identifiedVisitor: { success: boolean; visitor_id: string; message: string } | null = null;

export function getPublicConfig() {
  if (!publicConfigPromise) {
    publicConfigPromise = customerRequest<PublicConfig>("/api/public/config").catch((error) => {
      publicConfigPromise = null;
      throw error;
    });
  }
  return publicConfigPromise;
}

export function identifyVisitor() {
  return identifyRequest<{ success: boolean; visitor_id: string; message: string }>();
}

export function ensureVisitorIdentified(options: { force?: boolean } = {}) {
  if (!options.force && identifiedVisitor) {
    return Promise.resolve(identifiedVisitor);
  }
  if (!identifyPromise) {
    identifyPromise = identifyVisitor()
      .then((response) => {
        identifiedVisitor = response;
        return response;
      })
      .finally(() => {
        identifyPromise = null;
      });
  }
  return identifyPromise;
}

export function getVisitorStatus() {
  return customerRequest<VisitorStatus>("/api/visitor/status");
}

export async function getVisitorStatusAfterIdentify() {
  await ensureVisitorIdentified();
  try {
    return await getVisitorStatus();
  } catch (error) {
    if (error instanceof Error && "status" in error) {
      const status = Number((error as { status?: unknown }).status);
      if (status === 401 || status === 404) {
        identifiedVisitor = null;
        await ensureVisitorIdentified({ force: true });
        return getVisitorStatus();
      }
    }
    throw error;
  }
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
