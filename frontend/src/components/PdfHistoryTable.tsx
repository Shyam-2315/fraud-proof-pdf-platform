import { Download } from "lucide-react";
import { API_BASE_URL, getAccessToken } from "../api/client";
import { sendBehaviorEvent } from "../api/userApi";
import type { PdfHistoryItem } from "../api/userApi";
import { getIdentityHeaders } from "../utils/visitorIdentity";

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

export default function PdfHistoryTable({ items }: { items: PdfHistoryItem[] }) {
  if (!items.length) {
    return <div className="panel p-6 text-sm font-bold text-[#52647f]">No PDFs generated yet.</div>;
  }

  return (
    <div className="panel table-wrap">
      <table>
        <thead>
          <tr>
            <th>PDF title</th>
            <th>File name</th>
            <th>Created</th>
            <th>Download</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.pdf_id}>
              <td className="font-bold text-[#10213f]">{item.title}</td>
              <td>{item.file_name}</td>
              <td>{formatDate(item.created_at)}</td>
              <td>
                {item.download_url ? (
                  <button className="btn-secondary py-2" onClick={() => downloadPdf(item)}>
                    <Download size={16} />
                    View
                  </button>
                ) : (
                  <span className="text-[#52647f]">Unavailable</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

async function downloadPdf(item: PdfHistoryItem) {
  await sendBehaviorEvent("DOWNLOAD_CLICKED", { pdf_id: item.pdf_id });
  const headers = new Headers(await getIdentityHeaders());
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE_URL}${item.download_url}`, {
    headers,
    credentials: "include",
  });
  if (!response.ok) return;
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = item.file_name || `${item.pdf_id}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
