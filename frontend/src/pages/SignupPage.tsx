import { Link, useLocation, useNavigate } from "react-router-dom";
import AuthForm from "../components/AuthForm";
import ErrorState from "../components/ErrorState";
import Footer from "../components/Footer";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import { useState } from "react";
import { sendBehaviorEvent } from "../api/userApi";

export default function SignupPage() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState("");
  const state = location.state as { from?: string } | null;

  return (
    <div>
      <Navbar />
      <main className="shell grid gap-8 py-10 lg:grid-cols-[1.1fr_420px] lg:items-start">
        <section className="rounded-[28px] bg-[linear-gradient(135deg,#0f2d63_0%,#1459d9_55%,#66a3ff_100%)] px-8 py-10 text-white shadow-[0_18px_60px_rgba(20,89,217,0.24)]">
          <p className="text-xs font-black uppercase text-[#c9dcff]" style={{ letterSpacing: "0.24em" }}>Start free</p>
          <h1 className="mt-3 text-3xl font-black">Create your PDFCraft account</h1>
          <p className="mt-4 max-w-xl text-sm font-semibold text-[#dce8ff]">
            Create an account, verify your email, and keep your generated PDFs, history, and monthly usage in one place.
          </p>
          <div className="mt-8 grid gap-3 text-sm font-semibold text-[#eff5ff]">
            <div className="rounded-2xl border border-white/20 bg-white/10 px-4 py-3">
              5 PDFs included on the Free plan each month.
            </div>
            <div className="rounded-2xl border border-white/20 bg-white/10 px-4 py-3">
              Email verification keeps account access clean and recoverable.
            </div>
          </div>
          <p className="mt-8 text-sm font-semibold text-[#dce8ff]">
            Already have an account? <Link className="font-black text-white underline underline-offset-4" to="/login">Login</Link>.
          </p>
        </section>
        <section>
          {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}
          <AuthForm
            mode="signup"
            onSubmit={async ({ full_name, email, password }) => {
              try {
                void sendBehaviorEvent("SIGNUP_CLICKED");
                setError("");
                const response = await signup(full_name, email, password);
                navigate(`/verify-email?email=${encodeURIComponent(response.email)}`, {
                  replace: true,
                  state: {
                    email: response.email,
                    from: state?.from,
                    flashMessage: "We sent a verification code to your email.",
                    sentAt: Date.now(),
                  },
                });
              } catch (err) {
                setError(err instanceof Error ? err.message : "Signup failed.");
              }
            }}
          />
        </section>
      </main>
      <Footer />
    </div>
  );
}
