import { KeyRound } from "lucide-react";
import { FormEvent, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { login as loginRequest } from "../api/authApi";
import { clearAdminKey, setAdminAccessToken, setAdminKey } from "../api/client";
import ErrorState from "../components/ErrorState";

export default function AdminLoginPage() {
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
      if (email && password) {
        const response = await loginRequest({ email, password });
        if (response.user.role !== "ADMIN") {
          setError("Admin access required");
          return;
        }
        clearAdminKey();
        setAdminAccessToken(response.access_token);
        navigate(state?.from || "/admin/dashboard", { replace: true });
        return;
      }
      if (key.trim()) {
        setAdminKey(key.trim());
        navigate(state?.from || "/admin/dashboard", { replace: true });
        return;
      }
      setError("Enter admin email/password or an admin API key.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Admin login failed.");
    }
  }

  return (
    <main className="min-h-screen bg-[#12192a] px-4 py-16 text-white">
      <section className="mx-auto max-w-md rounded-lg border border-[#2e3d5d] bg-[#18223a] p-6 shadow-2xl">
        <div className="mb-6">
          <div className="mb-4 inline-flex rounded-lg bg-white p-2 text-[#1459d9]">
            <KeyRound size={24} />
          </div>
          <h1 className="text-2xl font-black">Internal Admin Access</h1>
          <p className="mt-2 text-sm font-semibold text-[#c7d3e7]">Use admin credentials or the local API key fallback.</p>
        </div>
        {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}
        {state?.message ? (
          <div className="mb-4 rounded-lg border border-[#f3c26b] bg-[#3b2d12] p-3 text-sm font-bold text-[#ffe2a6]">
            {state.message}
          </div>
        ) : null}
        <form onSubmit={submit}>
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
          <div className="mb-5 border-t border-[#2e3d5d]" />
          <label className="mb-5 block">
            <span className="mb-2 block text-sm font-black">Admin API Key fallback</span>
            <input
              className="field text-[#10213f]"
              type="password"
              value={key}
              onChange={(event) => setKey(event.target.value)}
            />
          </label>
          <button className="btn-primary w-full">
            <KeyRound size={18} />
            Continue
          </button>
        </form>
      </section>
    </main>
  );
}
