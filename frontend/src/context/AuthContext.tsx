import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";
import * as authApi from "../api/authApi";
import {
  clearAuthTokens,
  getAccessToken,
  getRefreshToken,
  setAuthTokens,
} from "../api/client";

type AuthContextValue = {
  user: authApi.AuthUser | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<authApi.AuthUser>;
  signup: (full_name: string, email: string, password: string) => Promise<authApi.RegisterResponse>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<authApi.AuthUser | null>(null);
  const [loading, setLoading] = useState(Boolean(getAccessToken()));

  async function refreshUser() {
    if (!getAccessToken()) {
      setUser(null);
      return;
    }
    const currentUser = await authApi.me();
    setUser(currentUser);
  }

  useEffect(() => {
    async function load() {
      try {
        await refreshUser();
      } catch {
        clearAuthTokens();
        setUser(null);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      isAuthenticated: Boolean(user),
      async login(email, password) {
        const response = await authApi.login({ email, password });
        setAuthTokens(response.access_token, response.refresh_token);
        setUser(response.user);
        return response.user;
      },
      async signup(full_name, email, password) {
        return authApi.register({ full_name, email, password });
      },
      async logout() {
        const refreshToken = getRefreshToken();
        try {
          if (refreshToken) await authApi.logout(refreshToken);
        } finally {
          clearAuthTokens();
          setUser(null);
        }
      },
      refreshUser,
    }),
    [user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
