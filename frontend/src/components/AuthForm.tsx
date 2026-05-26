import { FormEvent, useEffect, useState } from "react";

export default function AuthForm({
  mode,
  onSubmit,
  initialEmail = "",
}: {
  mode: "login" | "signup";
  onSubmit: (values: { full_name: string; email: string; password: string }) => Promise<void>;
  initialEmail?: string;
}) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState(initialEmail);
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [fieldError, setFieldError] = useState("");

  useEffect(() => {
    setEmail(initialEmail);
  }, [initialEmail]);

  function validate() {
    if (mode === "signup" && !fullName.trim()) {
      return "Full name is required.";
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      return "Please enter a valid email address.";
    }
    if (!password) {
      return "Password is required.";
    }
    if (mode === "signup" && password.length < 8) {
      return "Password must be at least 8 characters.";
    }
    return "";
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const validationError = validate();
    if (validationError) {
      setFieldError(validationError);
      return;
    }
    setSubmitting(true);
    setFieldError("");
    try {
      await onSubmit({ full_name: fullName.trim(), email: email.trim(), password });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="panel p-5" onSubmit={submit}>
      {fieldError ? (
        <div className="mb-4 rounded-lg border border-[#f0b6b6] bg-[#fff1f1] p-4 text-sm font-bold text-[#8b1e1e]">
          {fieldError}
        </div>
      ) : null}
      {mode === "signup" ? (
        <label className="mb-4 block">
          <span className="mb-2 block text-sm font-black text-[#21324e]">Full name</span>
          <input
            className="field"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            required
            minLength={2}
            placeholder="Jordan Lee"
          />
        </label>
      ) : null}
      <label className="mb-4 block">
        <span className="mb-2 block text-sm font-black text-[#21324e]">Email</span>
        <input
          className="field"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
          autoComplete="email"
          placeholder="you@example.com"
        />
      </label>
      <label className="mb-5 block">
        <span className="mb-2 block text-sm font-black text-[#21324e]">Password</span>
        <input
          className="field"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
          minLength={mode === "signup" ? 8 : undefined}
          autoComplete={mode === "signup" ? "new-password" : "current-password"}
          placeholder={mode === "signup" ? "At least 8 characters" : "Enter your password"}
        />
      </label>
      <button className="btn-primary w-full disabled:cursor-not-allowed disabled:opacity-70" disabled={submitting}>
        {submitting ? "Please wait..." : mode === "signup" ? "Create Account" : "Login"}
      </button>
    </form>
  );
}
