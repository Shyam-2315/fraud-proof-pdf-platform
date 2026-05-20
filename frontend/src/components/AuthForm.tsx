import { FormEvent, useState } from "react";

export default function AuthForm({
  mode,
  onSubmit,
}: {
  mode: "login" | "signup";
  onSubmit: (values: { full_name: string; email: string; password: string }) => Promise<void>;
}) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    try {
      await onSubmit({ full_name: fullName, email, password });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="panel p-5" onSubmit={submit}>
      {mode === "signup" ? (
        <label className="mb-4 block">
          <span className="mb-2 block text-sm font-black text-[#21324e]">Full name</span>
          <input className="field" value={fullName} onChange={(event) => setFullName(event.target.value)} required />
        </label>
      ) : null}
      <label className="mb-4 block">
        <span className="mb-2 block text-sm font-black text-[#21324e]">Email</span>
        <input className="field" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
      </label>
      <label className="mb-5 block">
        <span className="mb-2 block text-sm font-black text-[#21324e]">Password</span>
        <input className="field" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8} />
      </label>
      <button className="btn-primary w-full" disabled={submitting}>
        {submitting ? "Please wait..." : mode === "signup" ? "Create Account" : "Login"}
      </button>
    </form>
  );
}
