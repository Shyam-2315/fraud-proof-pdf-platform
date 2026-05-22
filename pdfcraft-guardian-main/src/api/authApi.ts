import { adminRequest } from "./client";

export type AdminLoginResponse = {
  access_token: string;
  user: {
    id?: string;
    user_id?: string;
    email: string;
    role: string;
  };
};

export const authApi = {
  login: (email: string, password: string) =>
    adminRequest<AdminLoginResponse>(
      "/api/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }) },
      { auth: false },
    ),
  me: () => adminRequest<AdminLoginResponse["user"]>("/api/auth/me"),
};
