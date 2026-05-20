import { userApi } from "./client";

export interface AuthUser {
  user_id: string;
  email: string;
  full_name?: string;
  is_active?: boolean;
  is_verified?: boolean;
  created_at?: string;
}
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const { data } = await userApi.post<AuthResponse>("/api/auth/login", { email, password });
  return data;
}
export async function register(email: string, password: string, full_name: string): Promise<AuthResponse> {
  const { data } = await userApi.post<AuthResponse>("/api/auth/register", { email, password, full_name });
  return data;
}
