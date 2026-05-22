export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8025";

export const ADMIN_TOKEN_KEY = "admin_access_token";
export const ADMIN_API_KEY = "admin_api_key";

export class AdminApiError extends Error {
  status: number;
  body: unknown;

  constructor(message: string, status: number, body?: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

export function clearAdminAuth() {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(ADMIN_TOKEN_KEY);
  sessionStorage.removeItem(ADMIN_API_KEY);
}

export function isAdminAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
  return !!(sessionStorage.getItem(ADMIN_TOKEN_KEY) || sessionStorage.getItem(ADMIN_API_KEY));
}

function getAuthHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = sessionStorage.getItem(ADMIN_TOKEN_KEY);
  if (token) return { Authorization: `Bearer ${token}` };
  const apiKey = sessionStorage.getItem(ADMIN_API_KEY);
  if (apiKey) return { "X-Admin-API-Key": apiKey };
  return {};
}

function messageFromBody(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object") return fallback;
  const fields = body as Record<string, unknown>;
  return (
    (typeof fields.detail === "string" && fields.detail) ||
    (typeof fields.message === "string" && fields.message) ||
    fallback
  );
}

export async function adminRequest<T = unknown>(
  path: string,
  options: RequestInit = {},
  opts: { auth?: boolean } = { auth: true },
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };

  if (opts.auth !== false) {
    Object.assign(headers, getAuthHeaders());
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  } catch {
    throw new AdminApiError(
      `Could not connect to backend at ${API_BASE_URL}. Please make sure backend is running.`,
      0,
    );
  }

  let body: unknown = null;
  const text = await response.text();
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }

  if (!response.ok) {
    if (response.status === 401 && opts.auth !== false) {
      clearAdminAuth();
      if (typeof window !== "undefined" && window.location.pathname !== "/admin/login") {
        window.location.href = "/admin/login?reason=auth";
      }
      throw new AdminApiError("Admin authentication required.", 401, body);
    }

    if (response.status === 403) {
      throw new AdminApiError("Invalid admin API key.", 403, body);
    }

    throw new AdminApiError(
      messageFromBody(body, `Request failed (${response.status})`),
      response.status,
      body,
    );
  }

  return body as T;
}
