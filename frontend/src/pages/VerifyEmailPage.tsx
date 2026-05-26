import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { getAuthErrorMessage, resendVerification, verifyEmail } from "../api/authApi";
import ErrorState from "../components/ErrorState";
import Footer from "../components/Footer";
import Navbar from "../components/Navbar";

export default function VerifyEmailPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as { email?: string; from?: string; flashMessage?: string; sentAt?: number } | null;
  const initialEmail = state?.email || new URLSearchParams(location.search).get("email") || "";
  const [email, setEmail] = useState(initialEmail);
  const [code, setCode] = useState("");
  const [message, setMessage] = useState(state?.flashMessage || "");
  const [error, setError] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [resending, setResending] = useState(false);
  const [verified, setVerified] = useState(false);
  const [cooldown, setCooldown] = useState(() => {
    if (!state?.sentAt) return 0;
    const remaining = 60 - Math.floor((Date.now() - state.sentAt) / 1000);
    return remaining > 0 ? remaining : 0;
  });

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = window.setInterval(() => {
      setCooldown((current) => (current > 0 ? current - 1 : 0));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [cooldown]);

  useEffect(() => {
    setEmail(initialEmail);
  }, [initialEmail]);

  const otpDigits = useMemo(() => Array.from({ length: 6 }, (_, index) => code[index] || ""), [code]);
  const canSubmit = email.trim().length > 0 && code.length === 6 && !verifying && !resending && !verified;
  const resendLabel = useMemo(() => {
    if (resending) return "Sending...";
    if (cooldown > 0) return `Resend in ${cooldown}s`;
    return "Resend code";
  }, [cooldown, resending]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setError("Please enter a valid email address.");
      return;
    }
    if (code.trim().length !== 6) {
      setError("Enter the full 6-digit verification code.");
      return;
    }
    setVerifying(true);
    setError("");
    setMessage("");
    try {
      const response = await verifyEmail({ email, code });
      setVerified(true);
      setMessage(response.message);
      window.setTimeout(() => {
        navigate("/login", {
          replace: true,
          state: {
            from: state?.from,
            email,
            flashMessage: "Email verified successfully. You can now log in.",
          },
        });
      }, 1600);
    } catch (err) {
      setVerified(false);
      setError(getAuthErrorMessage(err, "Verification could not be completed."));
    } finally {
      setVerifying(false);
    }
  }

  async function handleResend() {
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setError("Please enter a valid email address.");
      return;
    }
    setResending(true);
    setError("");
    setMessage("");
    try {
      const response = await resendVerification({ email });
      setMessage(response.message);
      setCooldown(60);
    } catch (err) {
      setError(getAuthErrorMessage(err, "A new code could not be sent right now."));
    } finally {
      setResending(false);
    }
  }

  return (
    <div>
      <Navbar />
      <main className="shell grid gap-8 py-10 lg:grid-cols-[1.05fr_420px] lg:items-start">
        <section className="rounded-[28px] border border-[#d6e3f8] bg-[linear-gradient(180deg,#ffffff_0%,#eef4ff_100%)] px-8 py-10 shadow-[0_18px_60px_rgba(16,33,63,0.08)]">
          <p className="text-xs font-black uppercase text-[#5373a8]" style={{ letterSpacing: "0.24em" }}>Email verification</p>
          <h1 className="mt-3 text-3xl font-black text-[#10213f]">Confirm your email</h1>
          <p className="mt-4 max-w-xl text-sm font-semibold text-[#52647f]">
            Enter the 6-digit code we sent to your inbox to activate your account and continue to login.
          </p>
          <div className="mt-8 grid gap-3 text-sm font-semibold text-[#405272]">
            <div className="rounded-2xl border border-[#d7e3f8] bg-white px-4 py-3">
              Codes expire quickly for safety, and you can request a fresh one if needed.
            </div>
            <div className="rounded-2xl border border-[#d7e3f8] bg-white px-4 py-3">
              Check spam or promotions if the email has not arrived yet.
            </div>
          </div>
          <p className="mt-8 text-sm font-semibold text-[#52647f]">
            Need a different address? <Link className="font-black text-[#1459d9]" to="/signup">Create a new account</Link>.
          </p>
        </section>
        <section>
          {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}
          {message ? (
            <div className="mb-4 rounded-lg border border-[#b8e2c8] bg-[#effaf3] p-4 text-sm font-bold text-[#17633a]">
              {message}
            </div>
          ) : null}
          <form className="panel p-6" onSubmit={submit}>
            <div className="mb-5 rounded-2xl bg-[#f6f9ff] p-4">
              <div className="text-xs font-black uppercase text-[#6580ab]" style={{ letterSpacing: "0.2em" }}>Step 2 of 2</div>
              <div className="mt-2 text-sm font-semibold text-[#405272]">
                {verified
                  ? "Email verified successfully. You can now log in."
                  : "Use the code from your email to finish setting up your account."}
              </div>
            </div>
            <label className="mb-4 block">
              <span className="mb-2 block text-sm font-black text-[#21324e]">Email</span>
              <input
                className="field"
                type="email"
                value={email}
                onChange={(event) => {
                  setEmail(event.target.value);
                  if (error) setError("");
                }}
                required
                autoComplete="email"
              />
            </label>
            <label className="mb-5 block">
              <span className="mb-2 block text-sm font-black text-[#21324e]">Verification code</span>
              <div className="relative">
                <input
                  className="otp-input-overlay"
                  inputMode="numeric"
                  maxLength={6}
                  pattern="[0-9]{6}"
                  value={code}
                  onChange={(event) => {
                    setCode(event.target.value.replace(/\D/g, "").slice(0, 6));
                    if (error) setError("");
                  }}
                  placeholder="123456"
                  required
                  autoComplete="one-time-code"
                  aria-label="6-digit verification code"
                />
                <div className="otp-grid" aria-hidden="true">
                  {otpDigits.map((digit, index) => (
                    <div
                      key={index}
                      className={`otp-slot ${digit ? "otp-slot-filled" : ""} ${index === code.length && !verified ? "otp-slot-active" : ""}`}
                    >
                      {digit || " "}
                    </div>
                  ))}
                </div>
              </div>
              <span className="mt-2 block text-xs font-semibold text-[#6a7d99]">
                Enter the latest 6-digit code sent to your email.
              </span>
            </label>
            <div className="flex flex-wrap gap-3">
              <button className="btn-primary disabled:cursor-not-allowed disabled:opacity-70" disabled={!canSubmit}>
                {verifying ? "Verifying..." : "Verify Email"}
              </button>
              <button
                className="btn-secondary disabled:cursor-not-allowed disabled:opacity-70"
                type="button"
                disabled={verifying || resending || cooldown > 0 || verified}
                onClick={() => void handleResend()}
              >
                {resendLabel}
              </button>
            </div>
          </form>
        </section>
      </main>
      <Footer />
    </div>
  );
}
