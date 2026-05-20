import { createFileRoute, useRouter } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { setAdminKey, getAdminKey, adminApi } from "@/api/client";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, Shield } from "lucide-react";

export const Route = createFileRoute("/admin/login")({ component: AdminLogin });

function AdminLogin() {
  const router = useRouter();
  const [key, setKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (getAdminKey()) router.navigate({ to: "/admin/dashboard" });
  }, [router]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null); setLoading(true);
    setAdminKey(key.trim());
    try {
      await adminApi.get("/api/admin/fraud/summary");
      router.navigate({ to: "/admin/dashboard" });
    } catch (err) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const e = err as any;
      const status = e?.response?.status;
      sessionStorage.removeItem("admin_api_key");
      window.dispatchEvent(new Event("admin-auth-change"));
      if (status === 401) setError("Admin API key required.");
      else if (status === 403) setError("Invalid admin API key.");
      else if (e?.code === "ERR_NETWORK") setError("Backend unavailable. Please start FastAPI on port 8025.");
      else setError(e?.message || "Login failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center bg-slate-100 px-6 py-16">
      <Card className="w-full max-w-md p-8 bg-white border-slate-200 shadow-md">
        <div className="flex items-center gap-2 text-slate-900">
          <Shield className="h-5 w-5 text-emerald-600" />
          <h1 className="text-xl font-semibold">Admin sign in</h1>
        </div>
        <p className="text-sm text-slate-600 mt-1">Enter your admin API key to access the fraud dashboard.</p>
        {error && <Alert className="mt-4 border-red-200 bg-red-50 text-red-800"><AlertDescription>{error}</AlertDescription></Alert>}
        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <div>
            <Label htmlFor="key">Admin API key</Label>
            <Input id="key" type="password" autoComplete="off" value={key} onChange={(e) => setKey(e.target.value)} required />
          </div>
          <Button type="submit" disabled={loading || !key} className="w-full bg-slate-900 hover:bg-slate-800 text-white">
            {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />} Continue
          </Button>
        </form>
        <p className="mt-4 text-xs text-slate-500">Key is stored in sessionStorage and cleared when you close the tab.</p>
      </Card>
    </div>
  );
}
