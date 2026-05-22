"use client";

import { useQuery } from "@tanstack/react-query";
import { Check, Copy, LogOut, Shield, SlidersHorizontal, Users } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { AppShell } from "@/components/app-shell";
import { getMe, logout } from "@/lib/api";
import { useAppStore } from "@/lib/store";

const ROLES = [
  ["Owner", "Full workspace, billing, security, and deletion access"],
  ["Admin", "Manage users, API keys, ingestion, dashboards, alerts"],
  ["Analyst", "Create dashboards, saved queries, reports, and alerts"],
  ["Viewer", "Read dashboards and shared reports"]
];

const ROLE_BADGE: Record<string, string> = {
  owner: "bg-purple-100 text-purple-800",
  admin: "bg-blue-100 text-blue-800",
  analyst: "bg-teal-100 text-teal-800",
  viewer: "bg-slate-100 text-slate-600"
};

export default function SettingsPage() {
  const router = useRouter();
  const { accessToken, organizationId, clear } = useAppStore();

  useEffect(() => {
    if (!accessToken) router.replace("/login" as never);
  }, [accessToken, router]);

  const { data: me } = useQuery({
    queryKey: ["me", accessToken],
    queryFn: () => getMe(accessToken!),
    enabled: !!accessToken
  });

  async function handleLogout() {
    try {
      if (accessToken) await logout(accessToken);
    } finally {
      clear();
      router.replace("/login" as never);
    }
  }

  return (
    <AppShell>
      <div className="mb-5">
        <h1 className="text-2xl font-semibold tracking-normal">Settings</h1>
        <p className="mt-1 text-sm text-muted">Organization, access control, account</p>
      </div>

      <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded border border-line bg-white shadow-soft">
          <div className="flex h-12 items-center gap-2 border-b border-line px-4">
            <Users size={17} className="text-accent" aria-hidden />
            <h2 className="text-base font-semibold">Role hierarchy</h2>
          </div>
          <div className="divide-y divide-line">
            {ROLES.map(([role, description]) => (
              <div key={role} className="flex items-center justify-between gap-4 px-4 py-3">
                <div>
                  <div className="font-medium">{role}</div>
                  <div className="mt-1 text-sm text-muted">{description}</div>
                </div>
                <Check size={17} className="shrink-0 text-accent" />
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded border border-line bg-white p-4 shadow-soft">
            <div className="mb-3 flex items-center gap-2">
              <Shield size={17} className="text-accent" />
              <h2 className="text-base font-semibold">Your account</h2>
            </div>
            {me ? (
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-muted">Name</dt>
                  <dd className="font-medium">{me.full_name}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted">Email</dt>
                  <dd className="font-medium">{me.email}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted">Role</dt>
                  <dd>
                    <span className={`rounded px-2 py-0.5 text-xs font-semibold ${ROLE_BADGE[me.role] ?? ""}`}>
                      {me.role}
                    </span>
                  </dd>
                </div>
                <div className="flex items-center justify-between pt-1">
                  <dt className="text-muted">Org ID</dt>
                  <dd className="flex items-center gap-1.5">
                    <code className="truncate max-w-[140px] text-xs">{organizationId}</code>
                    <button
                      onClick={() => navigator.clipboard.writeText(organizationId)}
                      className="text-muted hover:text-ink"
                      title="Copy"
                    >
                      <Copy size={13} />
                    </button>
                  </dd>
                </div>
              </dl>
            ) : (
              <p className="text-sm text-muted">Loading…</p>
            )}
            <button
              onClick={handleLogout}
              className="focus-ring mt-4 inline-flex w-full items-center justify-center gap-2 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-100"
            >
              <LogOut size={14} />
              Sign out
            </button>
          </div>
        </div>
      </section>

      <section className="mt-4 rounded border border-line bg-white p-4 shadow-soft">
        <div className="mb-3 flex items-center gap-2">
          <SlidersHorizontal size={17} className="text-accent" />
          <h2 className="text-base font-semibold">API reference</h2>
        </div>
        <p className="text-sm text-muted">
          Interactive Swagger UI:{" "}
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-accent hover:underline"
          >
            localhost:8000/docs
          </a>
          {" · "}
          ReDoc:{" "}
          <a
            href="http://localhost:8000/redoc"
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-accent hover:underline"
          >
            localhost:8000/redoc
          </a>
        </p>
      </section>
    </AppShell>
  );
}
