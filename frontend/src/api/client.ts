import { getIdentityHeaders, getVisitorIdentity } from "../utils/visitorIdentity";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8025";

export function apiUrl(path: string): string {
  const cleanBase = API_BASE_URL.replace(/\/$/, "");
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return `${cleanBase}${cleanPath}`;
}

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown) {
    super(typeof body === "object" && body && "message" in body ? String((body as { message: unknown }).message) : `Request failed with ${status}`);
    this.status = status;
    this.body = body;
  }
}

const ACCESS_TOKEN_KEY = "pdfcraft_access_token";
const REFRESH_TOKEN_KEY = "pdfcraft_refresh_token";

async function parseResponse(response: Response) {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

export async function customerRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  const identityHeaders = await getIdentityHeaders();
  Object.entries(identityHeaders).forEach(([key, value]) => headers.set(key, value));
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const accessToken = getAccessToken();
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  let response = await fetch(apiUrl(path), {
    ...init,
    headers,
    credentials: "include",
  });
  if (response.status === 401 && getRefreshToken()) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      headers.set("Authorization", `Bearer ${refreshed}`);
      response = await fetch(apiUrl(path), {
        ...init,
        headers,
        credentials: "include",
      });
    }
  }
  const body = await parseResponse(response);
  if (!response.ok) throw new ApiError(response.status, body);
  return body as T;
}

export async function identifyRequest<T>(): Promise<T> {
  const identity = await getVisitorIdentity();
  return customerRequest<T>("/api/visitor/identify", {
    method: "POST",
    body: JSON.stringify({
      local_storage_id: identity.localStorageId,
      session_id: identity.sessionId,
      fingerprint_hash: identity.fingerprintHash,
      device_profile_hash: identity.deviceProfileHash,
      canvas_hash: identity.canvasHash,
      webgl_hash: identity.webglHash,
      audio_hash: identity.audioHash,
      device_info: identity.deviceInfo,
      automation_signals: identity.automationSignals,
    }),
  });
}

export function getAccessToken() {
  return sessionStorage.getItem(ACCESS_TOKEN_KEY) || "";
}

export function getRefreshToken() {
  return sessionStorage.getItem(REFRESH_TOKEN_KEY) || "";
}

export function setAuthTokens(accessToken: string, refreshToken: string) {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  sessionStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearAuthTokens() {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  sessionStorage.removeItem(REFRESH_TOKEN_KEY);
}

async function refreshAccessToken() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return "";
  const response = await fetch(apiUrl("/api/auth/refresh"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) {
    clearAuthTokens();
    return "";
  }
  const body = (await response.json()) as { access_token: string; refresh_token: string };
  setAuthTokens(body.access_token, body.refresh_token);
  return body.access_token;
}
