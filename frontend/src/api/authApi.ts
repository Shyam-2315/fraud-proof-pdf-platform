import { customerRequest } from "./client";

export type AuthUser = {
  id: string;
  user_id: string;
  email: string;
  full_name: string | null;
  role: "CUSTOMER" | "ADMIN";
  plan: "FREE" | "PRO" | "BUSINESS";
  is_active?: boolean;
  is_verified?: boolean;
};

export type AuthResponse = {
  success: boolean;
  message: string;
  user: AuthUser;
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export function register(payload: { email: string; full_name: string; password: string }) {
  return customerRequest<AuthResponse>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function login(payload: { email: string; password: string }) {
  return customerRequest<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function logout(refreshToken: string) {
  return customerRequest<{ success: boolean; message: string }>("/api/auth/logout", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export function me() {
  return customerRequest<AuthUser>("/api/auth/me");
}

export type AccountUsage = {
  plan: string;
  month_key: string;
  used: number;
  limit: number;
  remaining: number;
  requires_upgrade: boolean;
};

export function getAccountUsage() {
  return customerRequest<AccountUsage>("/api/account/usage");
}
