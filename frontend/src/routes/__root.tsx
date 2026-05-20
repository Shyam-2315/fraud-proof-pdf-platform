import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  useLocation,
  HeadContent,
  Scripts,
} from "@tanstack/react-router";
import { useEffect } from "react";

import appCss from "../styles.css?url";
import { Navbar } from "@/components/Navbar";
import { AdminNavbar } from "@/components/AdminNavbar";
import { Toaster } from "@/components/ui/sonner";
import { identifyVisitor } from "@/api/userApi";
import { getAdminKey } from "@/api/client";

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-7xl font-bold text-foreground">404</h1>
        <h2 className="mt-4 text-xl font-semibold text-foreground">Page not found</h2>
        <p className="mt-2 text-sm text-muted-foreground">The page you're looking for doesn't exist.</p>
        <div className="mt-6">
          <Link to="/" className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90">Go home</Link>
        </div>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  console.error(error);
  const router = useRouter();
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-xl font-semibold text-foreground">This page didn't load</h1>
        <p className="mt-2 text-sm text-muted-foreground">{error.message}</p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <button onClick={() => { router.invalidate(); reset(); }} className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90">Try again</button>
          <a href="/" className="inline-flex items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium text-foreground hover:bg-accent">Go home</a>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "PDFCraft — Create professional PDFs instantly" },
      { name: "description", content: "Turn your text into clean, downloadable PDFs in seconds. Start with 2 free PDFs." },
    ],
    links: [{ rel: "stylesheet", href: appCss }],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootShell({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head><HeadContent /></head>
      <body>{children}<Scripts /></body>
    </html>
  );
}

function VisitorBootstrap() {
  useEffect(() => {
    identifyVisitor().catch((e) => console.warn("Visitor identify failed:", e?.message));
  }, []);
  return null;
}

function RootComponent() {
  const { queryClient } = Route.useRouteContext();
  const location = useLocation();
  const isAdminArea = location.pathname.startsWith("/admin");
  const isAdminLogin = location.pathname === "/admin/login";
  const showAdminNav = isAdminArea && !isAdminLogin && !!getAdminKey();

  return (
    <QueryClientProvider client={queryClient}>
      {!isAdminArea && <VisitorBootstrap />}
      <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
        {isAdminArea ? (showAdminNav && <AdminNavbar />) : <Navbar />}
        <main className="flex-1">
          <Outlet />
        </main>
        {!isAdminArea && (
          <footer className="border-t border-slate-200 bg-white">
            <div className="max-w-7xl mx-auto px-6 py-6 text-sm text-slate-500 flex flex-wrap justify-between gap-2">
              <span>© PDFCraft</span>
              <span>Create clean, professional PDFs in seconds.</span>
            </div>
          </footer>
        )}
      </div>
      <Toaster />
    </QueryClientProvider>
  );
}
