import { FormEvent, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { resendVerification, verifyEmail } from "../api/authApi";
import ErrorState from "../components/ErrorState";
import Footer from "../components/Footer";
import Navbar from "../components/Navbar";

export default function VerifyEmailPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as { email?: string; from?: string } | null;
  const initialEmail = state?.email || new URLSearchParams(location.search).get("email") || "";
  const [email, setEmail] = useState(initialEmail);
  const [code, setCode] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [resending, setResending] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setVerifying(true);
    setError("");
    setMessage("");
    try {
      const response = await verifyEmail({ email, code });
      setMessage(response.message);
      window.setTimeout(() => {
        navigate("/login", {
          replace: true,
          state: { from: state?.from, email },
        });
      }, 1200);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed.");
    } finally {
      setVerifying(false);
    }
  }

  async function handleResend() {
    setResending(true);
    setError("");
    setMessage("");
    try {
      const response = await resendVerification({ email });
      setMessage(response.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to resend code.");
    } finally {
      setResending(false);
    }
  }

  return (
    <div>
      <Navbar />
      <main className="shell grid gap-8 py-10 lg:grid-cols-[1fr_420px] lg:items-start">
        <section>
          <h1 className="text-3xl font-black text-[#10213f]">Verify your email</h1>
          <p className="mt-3 max-w-xl text-sm font-semibold text-[#52647f]">
            Enter the verification code sent to your email.
          </p>
          <p className="mt-6 text-sm font-semibold text-[#52647f]">
            Need to update your address? <Link className="font-black text-[#1459d9]" to="/signup">Create a new account</Link>.
          </p>
        </section>
        <section>
          {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}
          {message ? (
            <div className="mb-4 rounded-lg border border-[#b8e2c8] bg-[#effaf3] p-4 text-sm font-bold text-[#17633a]">
              {message}
            </div>
          ) : null}
          <form className="panel p-5" onSubmit={submit}>
            <label className="mb-4 block">
              <span className="mb-2 block text-sm font-black text-[#21324e]">Email</span>
              <input
                className="field"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </label>
            <label className="mb-5 block">
              <span className="mb-2 block text-sm font-black text-[#21324e]">Verification code</span>
              <input
                className="field tracking-[0.35em]"
                inputMode="numeric"
                maxLength={6}
                pattern="[0-9]{6}"
                value={code}
                onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                placeholder="123456"
                required
              />
            </label>
            <div className="flex flex-wrap gap-3">
              <button className="btn-primary" disabled={verifying || resending}>
                {verifying ? "Verifying..." : "Verify Email"}
              </button>
              <button
                className="btn-secondary"
                type="button"
                disabled={verifying || resending}
                onClick={() => void handleResend()}
              >
                {resending ? "Sending..." : "Resend Code"}
              </button>
            </div>
          </form>
        </section>
      </main>
      <Footer />
    </div>
  );
}
