import { KeyRound, LockKeyhole, Mail } from "lucide-react";
import { FormEvent, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { login as loginRequest } from "../api/authApi";
import { API_BASE_URL, clearAdminKey, clearAdminAccessToken, setAdminAccessToken, setAdminKey } from "../api/client";
import ErrorState from "../components/ErrorState";

export default function AdminLoginPage() {
  const [mode, setMode] = useState<"account" | "key">("account");
  const [key, setKey] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as { message?: string; from?: string } | null;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      if (mode === "account") {
        if (!email || !password) {
          setError("Enter admin email and password.");
          return;
        }
        const response = await loginRequest({ email, password });
        if (response.user.role !== "ADMIN") {
          setError("Admin access required.");
          return;
        }
        clearAdminKey();
        setAdminAccessToken(response.access_token);
        navigate(state?.from || "/admin/dashboard", { replace: true });
        return;
      }
      if (!key.trim()) {
        setError("Enter an admin API key.");
        return;
      }
      const isValid = await validateAdminKey(key.trim());
      if (!isValid) {
        clearAdminKey();
        clearAdminAccessToken();
        setError("Invalid admin API key.");
        return;
      }
      clearAdminAccessToken();
      setAdminKey(key.trim());
      navigate(state?.from || "/admin/dashboard", { replace: true });
    } catch (err) {
      setError(normalizeAdminLoginError(err));
    }
  }

  return (
    <main className="min-h-screen bg-[#12192a] px-4 py-16 text-white">
      <section className="mx-auto max-w-lg rounded-lg border border-[#2e3d5d] bg-[#18223a] p-6 shadow-2xl">
        <div className="mb-6">
          <div className="mb-4 inline-flex rounded-lg bg-white p-2 text-[#1459d9]">
            <KeyRound size={24} />
          </div>
          <h1 className="text-2xl font-black">PDFCraft Internal Admin</h1>
          <p className="mt-2 text-sm font-semibold text-[#c7d3e7]">Secure access for internal monitoring</p>
        </div>
        {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}
        {state?.message ? (
          <div className="mb-4 rounded-lg border border-[#f3c26b] bg-[#3b2d12] p-3 text-sm font-bold text-[#ffe2a6]">
            {state.message}
          </div>
        ) : null}
        <div className="mb-5 grid grid-cols-2 rounded-lg border border-[#2e3d5d] bg-[#12192a] p-1">
          <button
            className={`inline-flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-black ${mode === "account" ? "bg-white text-[#12192a]" : "text-[#c7d3e7]"}`}
            type="button"
            onClick={() => setMode("account")}
          >
            <Mail size={16} />
            Account Login
          </button>
          <button
            className={`inline-flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-black ${mode === "key" ? "bg-white text-[#12192a]" : "text-[#c7d3e7]"}`}
            type="button"
            onClick={() => setMode("key")}
          >
            <LockKeyhole size={16} />
            API Key Login
          </button>
        </div>
        <form onSubmit={submit}>
          {mode === "account" ? (
            <>
              <label className="mb-4 block">
                <span className="mb-2 block text-sm font-black">Admin Email</span>
                <input
                  className="field text-[#10213f]"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  autoFocus
                />
              </label>
              <label className="mb-5 block">
                <span className="mb-2 block text-sm font-black">Password</span>
                <input
                  className="field text-[#10213f]"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </label>
            </>
          ) : (
            <label className="mb-5 block">
              <span className="mb-2 block text-sm font-black">Admin API Key</span>
              <input
                className="field text-[#10213f]"
                type="password"
                value={key}
                onChange={(event) => setKey(event.target.value)}
                autoFocus
              />
            </label>
          )}
          <button className="btn-primary w-full">
            <KeyRound size={18} />
            Continue
          </button>
        </form>
      </section>
    </main>
  );
}

async function validateAdminKey(key: string) {
  const response = await fetch(`${API_BASE_URL}/api/admin/fraud/summary`, {
    headers: { "X-Admin-API-Key": key },
  });
  return response.ok;
}

function normalizeAdminLoginError(err: unknown) {
  const message = err instanceof Error ? err.message : "Admin login failed.";
  if (message.includes("401")) return "Admin credentials invalid.";
  if (message.includes("403") || message.includes("Admin access")) return "Admin access required.";
  return message || "Admin credentials invalid.";
}
