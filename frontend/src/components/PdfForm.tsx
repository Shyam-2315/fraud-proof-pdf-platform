import { FilePlus2 } from "lucide-react";
import { FormEvent, useRef, useState } from "react";
import { sendBehaviorEvent } from "../api/userApi";

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
  const titleTracked = useRef(false);

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
          onChange={(event) => {
            setTitle(event.target.value);
            if (!titleTracked.current && event.target.value.trim()) {
              titleTracked.current = true;
              void sendBehaviorEvent("PDF_TITLE_TYPED", { length: event.target.value.length });
            }
          }}
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
          onPaste={(event) => {
            const text = event.clipboardData.getData("text");
            void sendBehaviorEvent("PDF_CONTENT_PASTED", { length: text.length });
          }}
          placeholder="Paste the text for your PDF..."
          required
          disabled={disabled || submitting}
        />
      </label>
      <div className="flex flex-wrap gap-3">
        <button
          className="btn-primary"
          disabled={disabled || submitting}
          onClick={() => void sendBehaviorEvent("GENERATE_CLICKED", { title_length: title.length, content_length: content.length })}
        >
          <FilePlus2 size={18} />
          {submitting ? "Generating..." : "Generate PDF"}
        </button>
      </div>
    </form>
  );
}
