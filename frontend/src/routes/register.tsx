import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2 } from "lucide-react";
import { register } from "@/api/auth";
import { setAuthToken, getAuthToken } from "@/utils/authToken";
import { extractError } from "@/api/client";
import { toast } from "sonner";

export const Route = createFileRoute("/register")({ component: RegisterPage });

function RegisterPage() {
  const nav = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { if (getAuthToken()) nav({ to: "/generate" }); }, [nav]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true); setError(null);
    try {
      const res = await register(email, password, fullName);
      setAuthToken(res.access_token);
      toast.success("Account created.");
      nav({ to: "/generate" });
    } catch (err) {
      setError(extractError(err));
    } finally { setSubmitting(false); }
  };

  return (
    <div className="max-w-md mx-auto px-6 py-16">
      <Card className="p-8 bg-white border-slate-200 shadow-sm">
        <h1 className="text-2xl font-semibold text-slate-900">Create your account</h1>
        <p className="text-sm text-slate-600 mt-1">Unlock more PDF generations.</p>
        {error && <Alert className="mt-4 border-red-200 bg-red-50 text-red-800"><AlertDescription>{error}</AlertDescription></Alert>}
        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <div>
            <Label htmlFor="fullName">Full name</Label>
            <Input id="fullName" required value={fullName} onChange={(e) => setFullName(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="password">Password</Label>
            <Input id="password" type="password" required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <Button type="submit" disabled={submitting} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white">
            {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}Create account
          </Button>
        </form>
        <p className="mt-4 text-sm text-slate-600">
          Already have one? <Link to="/login" className="text-indigo-600 hover:underline">Sign in</Link>
        </p>
      </Card>
    </div>
  );
}
