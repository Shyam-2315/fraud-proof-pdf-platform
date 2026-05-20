import { Link, useNavigate } from "react-router-dom";
import AuthForm from "../components/AuthForm";
import ErrorState from "../components/ErrorState";
import Footer from "../components/Footer";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import { useState } from "react";

export default function SignupPage() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState("");

  return (
    <div>
      <Navbar />
      <main className="shell grid gap-8 py-10 lg:grid-cols-[1fr_420px] lg:items-start">
        <section>
          <h1 className="text-3xl font-black text-[#10213f]">Create your account</h1>
          <p className="mt-3 max-w-xl text-sm font-semibold text-[#52647f]">
            Get 5 PDFs per month on the Free plan and upgrade when you need more.
          </p>
          <p className="mt-6 text-sm font-semibold text-[#52647f]">
            Already have an account? <Link className="font-black text-[#1459d9]" to="/login">Login</Link>.
          </p>
        </section>
        <section>
          {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}
          <AuthForm
            mode="signup"
            onSubmit={async ({ full_name, email, password }) => {
              try {
                await signup(full_name, email, password);
                navigate("/account", { replace: true });
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
