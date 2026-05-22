"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DatabaseZap, KeyRound, RotateCw, Upload, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { StatusPill } from "@/components/status-pill";
import { createApiKey, ingestCsv, listApiKeys, listRecentEvents, revokeApiKey } from "@/lib/api";
import { useAppStore } from "@/lib/store";

function timeAgo(raw: string | null | undefined) {
  if (!raw) return "Never";
  const diff = Date.now() - new Date(raw).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function IngestionPage() {
  const router = useRouter();
  const { accessToken } = useAppStore();
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [newKeyName, setNewKeyName] = useState("");
  const [showNewKey, setShowNewKey] = useState(false);
  const [createdKey, setCreatedKey] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken) router.replace("/login" as never);
  }, [accessToken, router]);

  const { data: apiKeys = [], isLoading: keysLoading } = useQuery({
    queryKey: ["api-keys", accessToken],
    queryFn: () => listApiKeys(accessToken!),
    enabled: !!accessToken
  });

  const { data: recentEvents = [], isLoading: eventsLoading } = useQuery({
    queryKey: ["recent-events", accessToken],
    queryFn: () => listRecentEvents(accessToken!, 12),
    enabled: !!accessToken,
    refetchInterval: 30_000
  });

  const createKeyMut = useMutation({
    mutationFn: () => createApiKey(accessToken!, newKeyName),
    onSuccess: (data) => {
      setCreatedKey((data as unknown as { key: string }).key);
      setNewKeyName("");
      setShowNewKey(false);
      qc.invalidateQueries({ queryKey: ["api-keys"] });
    }
  });

  const revokeKeyMut = useMutation({
    mutationFn: (keyId: string) => revokeApiKey(accessToken!, keyId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["api-keys"] })
  });

  const csvMut = useMutation({
    mutationFn: (file: File) => ingestCsv(accessToken!, file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recent-events"] })
  });

  return (
    <AppShell>
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Ingestion</h1>
          <p className="mt-1 text-sm text-muted">API events, CSV uploads, webhook receivers</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => fileRef.current?.click()}
            className="focus-ring inline-flex items-center gap-2 rounded border border-line bg-white px-3 py-2 text-sm font-medium hover:bg-slate-50"
          >
            <Upload size={16} aria-hidden />
            {csvMut.isPending ? "Uploading…" : "CSV"}
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) csvMut.mutate(f);
            }}
          />
          <button
            onClick={() => setShowNewKey(true)}
            className="focus-ring inline-flex items-center gap-2 rounded bg-accent px-3 py-2 text-sm font-medium text-white hover:bg-teal-800"
          >
            <KeyRound size={16} aria-hidden />
            New key
          </button>
        </div>
      </div>

      {createdKey && (
        <div className="mb-4 flex items-start justify-between gap-3 rounded border border-teal-200 bg-teal-50 p-4">
          <div>
            <p className="text-sm font-semibold text-teal-800">API key created — copy it now, it won't be shown again</p>
            <code className="mt-1 block break-all text-xs text-teal-900">{createdKey}</code>
          </div>
          <button onClick={() => setCreatedKey(null)} className="text-teal-700 hover:text-teal-900">
            <X size={16} />
          </button>
        </div>
      )}

      {showNewKey && (
        <div className="mb-4 flex items-end gap-3 rounded border border-line bg-white p-4 shadow-soft">
          <div className="flex-1">
            <label className="mb-1 block text-sm font-medium">Key name</label>
            <input
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              className="focus-ring h-9 w-full rounded border border-line bg-slate-50 px-3 text-sm"
              placeholder="Production ingest"
            />
          </div>
          <button
            onClick={() => createKeyMut.mutate()}
            disabled={!newKeyName || createKeyMut.isPending}
            className="focus-ring rounded bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-50"
          >
            {createKeyMut.isPending ? "Creating…" : "Create"}
          </button>
          <button onClick={() => setShowNewKey(false)} className="text-muted hover:text-ink">
            <X size={16} />
          </button>
        </div>
      )}

      <section className="grid gap-4 lg:grid-cols-3">
        {[
          ["Single event endpoint", "/api/v1/ingest/event", "POST"],
          ["Batch endpoint", "/api/v1/ingest/batch", "POST"],
          ["Webhook receiver", "/api/v1/ingest/webhook/{source}", "POST"]
        ].map(([name, endpoint, method]) => (
          <div key={name} className="rounded border border-line bg-white p-4 shadow-soft">
            <div className="mb-3 flex items-center justify-between gap-3">
              <DatabaseZap size={18} className="text-accent" aria-hidden />
              <StatusPill value="active" />
            </div>
            <h2 className="font-semibold">{name}</h2>
            <div className="mt-2 flex items-center gap-2">
              <span className="rounded bg-teal-100 px-1.5 py-0.5 text-xs font-semibold text-teal-800">{method}</span>
              <code className="flex-1 rounded bg-slate-100 px-2 py-1 text-xs text-slate-700">{endpoint}</code>
            </div>
          </div>
        ))}
      </section>

      <section className="mt-4 rounded border border-line bg-white shadow-soft">
        <div className="flex h-12 items-center justify-between border-b border-line px-4">
          <h2 className="text-base font-semibold">API keys</h2>
          <button
            className="focus-ring inline-flex h-8 w-8 items-center justify-center rounded border border-line hover:bg-slate-50"
            onClick={() => qc.invalidateQueries({ queryKey: ["api-keys"] })}
            title="Refresh"
          >
            <RotateCw size={15} aria-label="Refresh" />
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Prefix</th>
                <th className="px-4 py-3 font-medium">Scopes</th>
                <th className="px-4 py-3 font-medium">Last used</th>
                <th className="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {keysLoading ? (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-sm text-muted">
                    Loading…
                  </td>
                </tr>
              ) : apiKeys.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-sm text-muted">
                    No API keys yet
                  </td>
                </tr>
              ) : (
                apiKeys.map((key) => (
                  <tr key={key.id} className={key.revoked_at ? "opacity-50" : ""}>
                    <td className="px-4 py-3 font-medium">{key.name}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-600">{key.prefix}…</td>
                    <td className="px-4 py-3 text-slate-600">{key.scopes.join(", ")}</td>
                    <td className="px-4 py-3 text-slate-600">{timeAgo(key.last_used_at)}</td>
                    <td className="px-4 py-3">
                      {!key.revoked_at && (
                        <button
                          onClick={() => revokeKeyMut.mutate(key.id)}
                          className="text-xs text-red-600 hover:underline"
                        >
                          Revoke
                        </button>
                      )}
                      {key.revoked_at && <span className="text-xs text-muted">Revoked</span>}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-4 rounded border border-line bg-white shadow-soft">
        <div className="border-b border-line px-4 py-3">
          <h2 className="text-base font-semibold">Recent events</h2>
        </div>
        <div className="grid gap-3 p-4 md:grid-cols-3">
          {eventsLoading ? (
            <p className="text-sm text-muted">Loading…</p>
          ) : recentEvents.length === 0 ? (
            <p className="text-sm text-muted">No events yet. Start ingesting data via the API or CSV upload.</p>
          ) : (
            recentEvents.map((event) => (
              <div key={event.id} className="rounded border border-line p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="truncate text-sm font-semibold">{event.event_type}</div>
                  {event.processed && (
                    <span className="shrink-0 rounded bg-teal-50 px-1.5 py-0.5 text-xs text-teal-700">✓</span>
                  )}
                </div>
                <div className="mt-1 text-xs text-muted">{timeAgo(event.received_at)}</div>
                {event.user_external_id && (
                  <div className="mt-1 truncate text-xs text-slate-500">uid: {event.user_external_id}</div>
                )}
              </div>
            ))
          )}
        </div>
      </section>
    </AppShell>
  );
}
