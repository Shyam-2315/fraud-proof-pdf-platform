import { useEffect, useState, type FormEvent } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  adminApi,
  type AdminUserManagementItem,
  type AdminUserManagementListResponse,
} from "@/lib/adminApi";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  fmtDate,
  fmtNumber,
} from "@/components/admin/primitives";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export const Route = createFileRoute("/admin/users")({
  component: AdminUsersPage,
});

type Filters = {
  search: string;
  plan: string;
  status: string;
};

const DEFAULT_FILTERS: Filters = {
  search: "",
  plan: "",
  status: "",
};

function AdminUsersPage() {
  const [data, setData] = useState<AdminUserManagementListResponse | null>(null);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [activeFilters, setActiveFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyUserId, setBusyUserId] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const response = await adminApi.getAdminUsers({
        limit: 100,
        search: activeFilters.search || undefined,
        plan: activeFilters.plan || undefined,
        is_active: activeFilters.status === "active" ? true : activeFilters.status === "blocked" ? false : undefined,
      });
      setData(response);
    } catch (err: any) {
      setError(err?.message || "Failed to load users.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [activeFilters]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setActiveFilters(filters);
  };

  const setUserActive = async (user: AdminUserManagementItem, isActive: boolean) => {
    if (!isActive && !window.confirm(`Block ${user.email}?`)) return;
    setBusyUserId(user.user_id);
    setError(null);
    try {
      if (isActive) {
        await adminApi.unblockUser(user.user_id);
      } else {
        await adminApi.blockUser(user.user_id);
      }
      await load();
    } catch (err: any) {
      setError(err?.message || "User update failed.");
    } finally {
      setBusyUserId(null);
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">User Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-3 md:grid-cols-[1fr_160px_160px_auto]" onSubmit={submit}>
            <Input
              placeholder="Search email or name"
              value={filters.search}
              onChange={(event) => setFilters({ ...filters, search: event.target.value })}
            />
            <select
              className="h-10 rounded-md border border-input bg-background px-3 text-sm"
              value={filters.plan}
              onChange={(event) => setFilters({ ...filters, plan: event.target.value })}
            >
              <option value="">Any plan</option>
              <option value="FREE">FREE</option>
              <option value="PRO">PRO</option>
              <option value="BUSINESS">BUSINESS</option>
            </select>
            <select
              className="h-10 rounded-md border border-input bg-background px-3 text-sm"
              value={filters.status}
              onChange={(event) => setFilters({ ...filters, status: event.target.value })}
            >
              <option value="">Any status</option>
              <option value="active">Active</option>
              <option value="blocked">Blocked</option>
            </select>
            <Button type="submit">Apply</Button>
          </form>
        </CardContent>
      </Card>

      {error ? <ErrorState message={error} /> : null}
      {loading ? <LoadingState label="Loading users…" /> : null}
      {!loading && data ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Users ({fmtNumber(data.total)})</CardTitle>
          </CardHeader>
          <CardContent>
            {data.items.length === 0 ? (
              <EmptyState label="No users match these filters." />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>User</TableHead>
                    <TableHead>Plan</TableHead>
                    <TableHead>Usage</TableHead>
                    <TableHead>Verification</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Linked Visitors</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((user) => (
                    <UserRow
                      key={user.user_id}
                      user={user}
                      busy={busyUserId === user.user_id}
                      onSetActive={setUserActive}
                    />
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

function UserRow({
  user,
  busy,
  onSetActive,
}: {
  user: AdminUserManagementItem;
  busy: boolean;
  onSetActive: (user: AdminUserManagementItem, isActive: boolean) => Promise<void>;
}) {
  return (
    <TableRow>
      <TableCell>
        <div className="font-medium">{user.email}</div>
        <div className="text-xs text-muted-foreground">{user.full_name || "No name"}</div>
      </TableCell>
      <TableCell>
        <Badge variant="outline">{user.plan}</Badge>
      </TableCell>
      <TableCell className="text-xs">
        <div>
          {fmtNumber(user.used)} / {fmtNumber(user.limit)}
        </div>
        <div className="text-muted-foreground">{fmtNumber(user.remaining)} remaining</div>
      </TableCell>
      <TableCell>
        {user.email_verified || user.is_verified ? (
          <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
            Verified
          </Badge>
        ) : (
          <Badge className="bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
            Pending
          </Badge>
        )}
      </TableCell>
      <TableCell>
        {user.is_active ? (
          <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
            Active
          </Badge>
        ) : (
          <Badge className="bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300">
            Blocked
          </Badge>
        )}
      </TableCell>
      <TableCell>{fmtNumber(user.linked_visitor_count)}</TableCell>
      <TableCell className="whitespace-nowrap text-xs">{fmtDate(user.created_at)}</TableCell>
      <TableCell className="text-right">
        {user.is_active ? (
          <Button
            variant="destructive"
            size="sm"
            disabled={busy || user.role === "ADMIN"}
            onClick={() => void onSetActive(user, false)}
          >
            Block
          </Button>
        ) : (
          <Button
            variant="outline"
            size="sm"
            disabled={busy}
            onClick={() => void onSetActive(user, true)}
          >
            Unblock
          </Button>
        )}
      </TableCell>
    </TableRow>
  );
}
