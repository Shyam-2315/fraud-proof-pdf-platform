import { Link, useLocation, useNavigate } from "react-router-dom";
import AuthForm from "../components/AuthForm";
import ErrorState from "../components/ErrorState";
import Footer from "../components/Footer";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import { useState } from "react";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState("");
  const state = location.state as { from?: string } | null;

  return (
    <div>
      <Navbar />
      <main className="shell grid gap-8 py-10 lg:grid-cols-[1fr_420px] lg:items-start">
        <section>
          <h1 className="text-3xl font-black text-[#10213f]">Login to PDFCraft</h1>
          <p className="mt-3 max-w-xl text-sm font-semibold text-[#52647f]">
            Continue generating PDFs and manage your monthly usage.
          </p>
          <p className="mt-6 text-sm font-semibold text-[#52647f]">
            New to PDFCraft? <Link className="font-black text-[#1459d9]" to="/signup">Create an account</Link>.
          </p>
        </section>
        <section>
          {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}
          <AuthForm
            mode="login"
            onSubmit={async ({ email, password }) => {
              try {
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
