import { useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { adminApi } from "@/lib/adminApi";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { LoadingState, ErrorState, EmptyState, fmtDate } from "@/components/admin/primitives";

export const Route = createFileRoute("/admin/pdfs")({
  component: AdminPdfsPage,
});

function AdminPdfsPage() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await adminApi.getAllPdfs();
        const list = Array.isArray(res) ? res : res?.items || res?.pdfs || [];
        if (!cancelled) setItems(list);
      } catch (err: any) {
        if (!cancelled) setError(err?.message || "Failed to load PDFs.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = items.filter((p) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return (
      String(p.pdf_id || p.id || "").toLowerCase().includes(s) ||
      String(p.title || "").toLowerCase().includes(s) ||
      String(p.file_name || p.filename || "").toLowerCase().includes(s) ||
      String(p.visitor_id || "").toLowerCase().includes(s) ||
      String(p.user_id || "").toLowerCase().includes(s)
    );
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="flex flex-wrap items-center gap-3 p-4">
          <Input
            placeholder="Search PDFs…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-[260px]"
          />
          <Badge variant="secondary">{filtered.length} PDFs</Badge>
        </CardContent>
      </Card>

      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} />
      ) : filtered.length === 0 ? (
        <EmptyState label="No PDFs found." />
      ) : (
        <Card>
          <CardContent className="overflow-x-auto p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>PDF ID</TableHead>
                  <TableHead>Owner</TableHead>
                  <TableHead>User ID</TableHead>
                  <TableHead>Visitor ID</TableHead>
                  <TableHead>Title</TableHead>
                  <TableHead>File Name</TableHead>
                  <TableHead>Created At</TableHead>
                  <TableHead>IP</TableHead>
                  <TableHead>Fingerprint</TableHead>
                  <TableHead>Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((p: any, i: number) => (
                  <TableRow key={p.id || i}>
                    <TableCell className="font-mono text-xs">{p.pdf_id || p.id || "—"}</TableCell>
                    <TableCell className="text-xs">{p.owner_type || "—"}</TableCell>
                    <TableCell className="font-mono text-xs">{p.user_id || "—"}</TableCell>
                    <TableCell className="font-mono text-xs">
                      {p.visitor_id ? (
                        <Link
                          to="/admin/visitor/$visitorId"
                          params={{ visitorId: p.visitor_id }}
                          className="text-primary hover:underline"
                        >
                          {p.visitor_id}
                        </Link>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell className="text-xs">{p.title || "—"}</TableCell>
                    <TableCell className="font-mono text-xs">
                      {p.file_name || p.filename || "—"}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-xs">
                      {fmtDate(p.created_at)}
                    </TableCell>
                    <TableCell className="font-mono text-xs">{p.ip_address || "—"}</TableCell>
                    <TableCell className="font-mono text-xs">
                      {p.fingerprint_hash ? String(p.fingerprint_hash).slice(0, 12) + "…" : "—"}
                    </TableCell>
                    <TableCell>
                      {p.download_url || p.url ? (
                        <Button asChild size="sm" variant="outline">
                          <a href={p.download_url || p.url} target="_blank" rel="noreferrer">
                            View
                          </a>
                        </Button>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
