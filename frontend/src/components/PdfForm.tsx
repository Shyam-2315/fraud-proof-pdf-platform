import { FilePlus2, LogIn } from "lucide-react";
import { FormEvent, useState } from "react";

export type PdfFormValues = { title: string; content: string };

export default function PdfForm({
  disabled,
  onSubmit,
}: {
  disabled?: boolean;
  onSubmit: (values: PdfFormValues) => Promise<void>;
}) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    try {
      await onSubmit({ title, content });
      setTitle("");
      setContent("");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="panel p-5" onSubmit={submit}>
      <div className="mb-5">
        <h1 className="text-2xl font-black text-[#10213f]">Create a PDF</h1>
        <p className="text-sm font-semibold text-[#52647f]">
          Add a title, paste your content, and generate a clean document.
        </p>
      </div>
      <label className="mb-4 block">
        <span className="mb-2 block text-sm font-black text-[#21324e]">PDF title</span>
        <input
          className="field"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="Quarterly update"
          required
          disabled={disabled || submitting}
        />
      </label>
      <label className="mb-5 block">
        <span className="mb-2 block text-sm font-black text-[#21324e]">Content</span>
        <textarea
          className="field min-h-72 resize-y"
          value={content}
          onChange={(event) => setContent(event.target.value)}
          placeholder="Paste the text for your PDF..."
          required
          disabled={disabled || submitting}
        />
      </label>
      <div className="flex flex-wrap gap-3">
        <button className="btn-primary" disabled={disabled || submitting}>
          <FilePlus2 size={18} />
          {submitting ? "Generating..." : "Generate PDF"}
        </button>
        {disabled ? (
          <button className="btn-secondary" type="button">
            <LogIn size={18} />
            Login / Signup
          </button>
        ) : null}
      </div>
    </form>
  );
}
