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
  fraud_blocked?: boolean;
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
  return customerRequest<VisitorStatus>("/api/visitor/status").then(normalizeVisitorStatus);
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

export function getVisitorUsageSnapshot(status: Partial<VisitorStatus> | null) {
  const used = status?.used ?? status?.free_usage_count ?? 0;
  const limit = status?.free_limit ?? status?.free_usage_limit ?? 2;
  const remaining = status?.remaining ?? status?.remaining_free_uses ?? Math.max(limit - used, 0);
  return {
    used: Math.max(used, 0),
    remaining: Math.max(remaining, 0),
    freeLimit: Math.max(limit, 0),
  };
}

export function isVisitorStatusBlocked(status: Partial<VisitorStatus> | null) {
  if (!status) return false;
  const fraudBlocked = Boolean(status.fraud_blocked);
  const { remaining } = getVisitorUsageSnapshot(status);
  return fraudBlocked || remaining <= 0;
}

export function getVisitorStatusMessage(status: Partial<VisitorStatus> | null) {
  const { freeLimit } = getVisitorUsageSnapshot(status);
  return isVisitorStatusBlocked(status)
    ? status?.message || "Free limit reached. Please log in to continue."
    : `You can generate ${freeLimit} PDFs for free.`;
}

export function normalizeVisitorStatus(status: VisitorStatus): VisitorStatus {
  const usage = getVisitorUsageSnapshot(status);
  const blocked = isVisitorStatusBlocked(status);
  return {
    ...status,
    used: usage.used,
    remaining: usage.remaining,
    free_limit: usage.freeLimit,
    free_usage_count: usage.used,
    free_usage_limit: usage.freeLimit,
    remaining_free_uses: usage.remaining,
    is_blocked: blocked,
    requires_login: blocked,
    message: blocked ? status.message || "Free limit reached. Please log in to continue." : null,
  };
}
