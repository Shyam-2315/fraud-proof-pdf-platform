import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2 } from "lucide-react";
import { login } from "@/api/auth";
import { setAuthToken, getAuthToken } from "@/utils/authToken";
import { extractError } from "@/api/client";
import { toast } from "sonner";

export const Route = createFileRoute("/login")({ component: LoginPage });

function LoginPage() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { if (getAuthToken()) nav({ to: "/generate" }); }, [nav]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true); setError(null);
    try {
      const res = await login(email, password);
      setAuthToken(res.access_token);
      toast.success("Signed in.");
      nav({ to: "/generate" });
    } catch (err) {
      setError(extractError(err));
    } finally { setSubmitting(false); }
  };

  return (
    <div className="max-w-md mx-auto px-6 py-16">
      <Card className="p-8 bg-white border-slate-200 shadow-sm">
        <h1 className="text-2xl font-semibold text-slate-900">Sign in</h1>
        <p className="text-sm text-slate-600 mt-1">Continue generating PDFs with your account.</p>
        {error && <Alert className="mt-4 border-red-200 bg-red-50 text-red-800"><AlertDescription>{error}</AlertDescription></Alert>}
        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <div>
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="password">Password</Label>
            <Input id="password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <Button type="submit" disabled={submitting} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white">
            {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}Sign in
          </Button>
        </form>
        <p className="mt-4 text-sm text-slate-600">
          No account? <Link to="/register" className="text-indigo-600 hover:underline">Create one</Link>
        </p>
      </Card>
    </div>
  );
}
