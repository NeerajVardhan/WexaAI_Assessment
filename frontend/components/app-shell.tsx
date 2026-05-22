"use client";

import clsx from "clsx";
import {
  Activity,
  Bell,
  DatabaseZap,
  FileClock,
  Gauge,
  KeyRound,
  LayoutDashboard,
  Search,
  Settings
} from "lucide-react";
import type { Route } from "next";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

type NavigationItem = {
  href: Route;
  label: string;
  icon: typeof LayoutDashboard;
};

const navigation: NavigationItem[] = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/ingestion", label: "Ingestion", icon: DatabaseZap },
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/reports", label: "Reports", icon: FileClock },
  { href: "/settings", label: "Settings", icon: Settings }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <div className="min-h-screen bg-[#f6f8fb] text-ink">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 border-r border-line bg-white lg:block">
        <div className="flex h-16 items-center gap-3 border-b border-line px-5">
          <div className="flex h-9 w-9 items-center justify-center rounded bg-accent text-white">
            <Gauge size={19} aria-hidden />
          </div>
          <div>
            <div className="text-sm font-semibold">WexaAI Analytics</div>
            <div className="text-xs text-muted">Production workspace</div>
          </div>
        </div>
        <nav className="space-y-1 p-3">
          {navigation.map((item) => {
            const active = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  "flex h-10 items-center gap-3 rounded px-3 text-sm font-medium transition",
                  active ? "bg-slate-100 text-ink" : "text-slate-600 hover:bg-slate-50 hover:text-ink"
                )}
              >
                <Icon size={17} aria-hidden />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 border-b border-line bg-white/95 backdrop-blur">
          <div className="flex h-16 items-center gap-3 px-4 sm:px-6">
            <div className="relative min-w-0 flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
              <input
                className="focus-ring h-10 w-full max-w-xl rounded border border-line bg-slate-50 pl-9 pr-3 text-sm"
                placeholder="Search dashboards, events, alerts"
              />
            </div>
            <button
              onClick={() => router.push("/" as never)}
              title="Overview"
              className="focus-ring inline-flex h-10 w-10 items-center justify-center rounded border border-line bg-white hover:bg-slate-50"
            >
              <Activity size={17} aria-hidden />
            </button>
            <button
              onClick={() => router.push("/ingestion" as never)}
              title="API keys"
              className="focus-ring inline-flex h-10 w-10 items-center justify-center rounded border border-line bg-white hover:bg-slate-50"
            >
              <KeyRound size={17} aria-hidden />
            </button>
          </div>
        </header>
        <main className="px-4 py-5 sm:px-6">{children}</main>
      </div>
    </div>
  );
}
