import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { ShieldCheck, Loader2 } from "lucide-react";
import {
  authApi,
  API_BASE_URL,
  ADMIN_TOKEN_KEY,
  ADMIN_API_KEY,
  clearAdminAuth,
} from "@/lib/adminApi";
import { Toaster } from "@/components/ui/sonner";

export const Route = createFileRoute("/admin/login")({
  component: AdminLoginPage,
  validateSearch: (s: Record<string, unknown>) => ({ reason: (s.reason as string) || undefined }),
});

function AdminLoginPage() {
  const navigate = useNavigate();
  const search = Route.useSearch();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(
    search.reason === "auth" ? "Admin authentication required." : null,
  );

  const handleAccountLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await authApi.login(email, password);
      const role = res?.user?.role?.toUpperCase?.() || "";
      if (role !== "ADMIN") {
        setError("Admin access required.");
        return;
      }
      sessionStorage.setItem(ADMIN_TOKEN_KEY, res.access_token);
      sessionStorage.removeItem(ADMIN_API_KEY);
      toast.success("Welcome back, admin");
      navigate({ to: "/admin/dashboard" });
    } catch (err: any) {
      setError(err?.message || "Login failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleApiKeyLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!apiKey.trim()) {
      setError("Please enter an admin API key.");
      return;
    }
    setLoading(true);
    sessionStorage.setItem(ADMIN_API_KEY, apiKey.trim());
    sessionStorage.removeItem(ADMIN_TOKEN_KEY);
    try {
      await verifyAdminApiKey(apiKey.trim());
      toast.success("API key verified");
      navigate({ to: "/admin/dashboard" });
    } catch (err: any) {
      clearAdminAuth();
      if (err?.status === 401) {
        setError("Admin authentication required.");
      } else if (err?.status === 403) {
        setError("Invalid admin API key.");
      } else {
        setError(err?.message || "Could not verify API key.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader className="space-y-3 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <CardTitle className="text-2xl">PDFCraft Internal Admin</CardTitle>
          <CardDescription>Secure access for internal monitoring</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="account">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="account">Admin Account Login</TabsTrigger>
              <TabsTrigger value="apikey">API Key Login</TabsTrigger>
            </TabsList>

            <TabsContent value="account" className="mt-4">
              <form className="space-y-4" onSubmit={handleAccountLogin}>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    autoComplete="username"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>
                {error && <p className="text-sm text-destructive">{error}</p>}
                <Button type="submit" className="w-full" disabled={loading}>
                  {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Login
                </Button>
              </form>
            </TabsContent>

            <TabsContent value="apikey" className="mt-4">
              <form className="space-y-4" onSubmit={handleApiKeyLogin}>
                <div className="space-y-2">
                  <Label htmlFor="apikey">Admin API Key</Label>
                  <Input
                    id="apikey"
                    type="password"
                    autoComplete="off"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="Paste your admin API key"
                  />
                  <p className="text-xs text-muted-foreground">
                    API key login is for local demo and internal testing.
                  </p>
                </div>
                {error && <p className="text-sm text-destructive">{error}</p>}
                <Button type="submit" className="w-full" disabled={loading}>
                  {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Login
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
      <Toaster />
    </div>
  );
}

async function verifyAdminApiKey(key: string) {
  const response = await fetch(`${API_BASE_URL}/api/admin/fraud/summary`, {
    headers: { "X-Admin-API-Key": key },
  }).catch(() => {
    throw new Error(
      `Could not connect to backend at ${API_BASE_URL}. Please make sure backend is running.`,
    );
  });

  if (response.status === 401) {
    throw Object.assign(new Error("Admin authentication required."), { status: 401 });
  }

  if (response.status === 403) {
    throw Object.assign(new Error("Invalid admin API key."), { status: 403 });
  }

  if (!response.ok) {
    throw Object.assign(new Error(`Request failed (${response.status})`), {
      status: response.status,
    });
  }
}
