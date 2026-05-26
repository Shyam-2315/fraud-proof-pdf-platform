import { Link, useLocation, useNavigate } from "react-router-dom";
import AuthForm from "../components/AuthForm";
import ErrorState from "../components/ErrorState";
import Footer from "../components/Footer";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import { useState } from "react";
import { sendBehaviorEvent } from "../api/userApi";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState("");
  const [pendingEmail, setPendingEmail] = useState("");
  const state = location.state as { from?: string; email?: string; flashMessage?: string } | null;

  return (
    <div>
      <Navbar />
      <main className="shell grid gap-8 py-10 lg:grid-cols-[1.1fr_420px] lg:items-start">
        <section className="rounded-[28px] border border-[#d8e4f8] bg-[radial-gradient(circle_at_top_left,#f8fbff_0%,#edf4ff_40%,#ffffff_100%)] px-8 py-10 shadow-[0_18px_60px_rgba(16,33,63,0.08)]">
          <p className="text-xs font-black uppercase text-[#5373a8]" style={{ letterSpacing: "0.24em" }}>Welcome back</p>
          <h1 className="mt-3 text-3xl font-black text-[#10213f]">Login to PDFCraft</h1>
          <p className="mt-4 max-w-xl text-sm font-semibold text-[#52647f]">
            Pick up where you left off, review your PDF history, and keep everything under your verified account.
          </p>
          <div className="mt-8 grid gap-3 text-sm font-semibold text-[#405272]">
            <div className="rounded-2xl border border-[#d7e3f8] bg-white px-4 py-3">
              Verified accounts can log in and generate PDFs normally.
            </div>
            <div className="rounded-2xl border border-[#d7e3f8] bg-white px-4 py-3">
              If your email is still pending, you can jump straight back to verification.
            </div>
          </div>
          <p className="mt-8 text-sm font-semibold text-[#52647f]">
            New to PDFCraft? <Link className="font-black text-[#1459d9]" to="/signup">Create an account</Link>.
          </p>
        </section>
        <section>
          {state?.flashMessage ? (
            <div className="mb-4 rounded-lg border border-[#b8e2c8] bg-[#effaf3] p-4 text-sm font-bold text-[#17633a]">
              {state.flashMessage}
            </div>
          ) : null}
          {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}
          {error === "Please verify your email before logging in." && pendingEmail ? (
            <div className="mb-4 rounded-lg border border-[#ffe2a8] bg-[#fff6df] p-4 text-sm font-bold text-[#765000]">
              <div>Please verify your email before logging in.</div>
              <Link
                className="mt-3 inline-flex rounded-lg border border-[#1459d9] px-3 py-2 text-[#1459d9]"
                to={`/verify-email?email=${encodeURIComponent(pendingEmail)}`}
              >
                Verify email
              </Link>
            </div>
          ) : null}
          <AuthForm
            mode="login"
            initialEmail={state?.email || ""}
            onSubmit={async ({ email, password }) => {
              try {
                void sendBehaviorEvent("LOGIN_CLICKED");
                setError("");
                setPendingEmail(email);
                await login(email, password);
                navigate(state?.from || "/account", { replace: true });
              } catch (err) {
                setError(err instanceof Error ? err.message : "Login failed.");
              }
            }}
          />
        </section>
      </main>
      <Footer />
    </div>
  );
}
