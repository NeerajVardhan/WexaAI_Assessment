"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FileClock, Loader2, Play, Plus, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { createReport, listDashboards, listReportRuns, listReports, runReport } from "@/lib/api";
import { useAppStore } from "@/lib/store";

function timeAgo(raw: string | null | undefined) {
  if (!raw) return "Never";
  const diff = Date.now() - new Date(raw).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return new Date(raw).toLocaleDateString();
}

export default function ReportsPage() {
  const router = useRouter();
  const { accessToken } = useAppStore();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [expandedRuns, setExpandedRuns] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "",
    cron: "0 9 * * 1",
    format: "pdf" as "pdf" | "png",
    recipients: "",
    dashboard_id: ""
  });

  useEffect(() => {
    if (!accessToken) router.replace("/login" as never);
  }, [accessToken, router]);

  const { data: reports = [], isLoading } = useQuery({
    queryKey: ["reports", accessToken],
    queryFn: () => listReports(accessToken!),
    enabled: !!accessToken,
    refetchInterval: 60_000
  });

  const { data: dashboards = [] } = useQuery({
    queryKey: ["dashboards", accessToken],
    queryFn: () => listDashboards(accessToken!),
    enabled: !!accessToken
  });

  const { data: runs = [] } = useQuery({
    queryKey: ["report-runs", accessToken, expandedRuns],
    queryFn: () => listReportRuns(accessToken!, expandedRuns!),
    enabled: !!accessToken && !!expandedRuns
  });

  const createMut = useMutation({
    mutationFn: () =>
      createReport(accessToken!, {
        name: form.name,
        cron: form.cron,
        format: form.format,
        recipients: form.recipients
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        dashboard_id: form.dashboard_id || dashboards[0]?.id || null
      }),
    onSuccess: () => {
      setShowForm(false);
      setCreateError(null);
      setForm({ name: "", cron: "0 9 * * 1", format: "pdf", recipients: "", dashboard_id: "" });
      qc.invalidateQueries({ queryKey: ["reports"] });
    },
    onError: (err: Error) => {
      setCreateError(err.message ?? "Failed to create report schedule");
    }
  });

  const runNowMut = useMutation({
    mutationFn: (id: string) => runReport(accessToken!, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reports"] })
  });

  return (
    <AppShell>
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Scheduled reports</h1>
          <p className="mt-1 text-sm text-muted">Dashboard snapshots, recipients, archive</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="focus-ring inline-flex items-center gap-2 rounded bg-accent px-3 py-2 text-sm font-medium text-white hover:bg-teal-800"
        >
          <Plus size={16} aria-hidden />
          New report
        </button>
      </div>

      {showForm && (
        <div className="mb-4 rounded border border-line bg-white p-5 shadow-soft">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold">New report schedule</h2>
            <button onClick={() => setShowForm(false)} className="text-muted hover:text-ink">
              <X size={16} />
            </button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium">Name</label>
              <input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                className="focus-ring h-9 w-full rounded border border-line bg-slate-50 px-3 text-sm"
                placeholder="Weekly overview"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Cron expression</label>
              <input
                value={form.cron}
                onChange={(e) => setForm((f) => ({ ...f, cron: e.target.value }))}
                className="focus-ring h-9 w-full rounded border border-line bg-slate-50 px-3 font-mono text-sm"
                placeholder="0 9 * * 1"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Format</label>
              <select
                value={form.format}
                onChange={(e) => setForm((f) => ({ ...f, format: e.target.value as "pdf" | "png" }))}
                className="focus-ring h-9 w-full rounded border border-line bg-slate-50 px-2 text-sm"
              >
                <option value="pdf">PDF</option>
                <option value="png">PNG (CSV)</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Recipients (comma-separated)</label>
              <input
                value={form.recipients}
                onChange={(e) => setForm((f) => ({ ...f, recipients: e.target.value }))}
                className="focus-ring h-9 w-full rounded border border-line bg-slate-50 px-3 text-sm"
                placeholder="team@example.com"
              />
            </div>
            {dashboards.length > 0 && (
              <div>
                <label className="mb-1 block text-sm font-medium">Dashboard</label>
                <select
                  value={form.dashboard_id}
                  onChange={(e) => setForm((f) => ({ ...f, dashboard_id: e.target.value }))}
                  className="focus-ring h-9 w-full rounded border border-line bg-slate-50 px-2 text-sm"
                >
                  <option value="">— first dashboard —</option>
                  {dashboards.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
          {createError && (
            <p className="mt-3 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{createError}</p>
          )}
          <button
            onClick={() => { setCreateError(null); createMut.mutate(); }}
            disabled={!form.name || createMut.isPending}
            className="focus-ring mt-4 rounded bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-50"
          >
            {createMut.isPending ? "Creating…" : "Create schedule"}
          </button>
        </div>
      )}

      {isLoading ? (
        <div className="flex h-40 items-center justify-center">
          <Loader2 size={24} className="animate-spin text-muted" />
        </div>
      ) : reports.length === 0 ? (
        <div className="rounded border border-line bg-white p-12 text-center text-sm text-muted shadow-soft">
          No report schedules yet. Click "New report" to create one.
        </div>
      ) : (
        <section className="grid gap-4 lg:grid-cols-2">
          {reports.map((report) => (
            <div key={report.id} className="rounded border border-line bg-white p-4 shadow-soft">
              <div className="flex items-start justify-between gap-4">
                <div className="flex gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-slate-100 text-accent">
                    <FileClock size={18} aria-hidden />
                  </div>
                  <div>
                    <h2 className="font-semibold">{report.name}</h2>
                    <div className="mt-0.5 font-mono text-xs text-muted">{report.cron}</div>
                    <div className="mt-0.5 text-xs text-slate-500">{report.format.toUpperCase()}</div>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => runNowMut.mutate(report.id)}
                    disabled={runNowMut.isPending}
                    className="focus-ring inline-flex h-8 w-8 items-center justify-center rounded border border-line hover:bg-slate-50 disabled:opacity-50"
                    title="Run now"
                  >
                    {runNowMut.isPending ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                  </button>
                  <button
                    onClick={() => setExpandedRuns(expandedRuns === report.id ? null : report.id)}
                    className="focus-ring inline-flex h-8 w-8 items-center justify-center rounded border border-line hover:bg-slate-50"
                    title="Run history"
                  >
                    <Download size={14} />
                  </button>
                </div>
              </div>
              <div className="mt-4 grid gap-3 border-t border-line pt-4 sm:grid-cols-2">
                <div>
                  <div className="text-xs uppercase text-muted">Recipients</div>
                  <div className="mt-1 text-sm">
                    {report.recipients.length ? report.recipients.join(", ") : "None"}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase text-muted">Last run</div>
                  <div className="mt-1 text-sm">{timeAgo(report.last_run_at)}</div>
                </div>
              </div>
              {expandedRuns === report.id && (
                <div className="mt-3 border-t border-line pt-3">
                  <div className="text-xs font-semibold uppercase text-muted">Run history</div>
                  {runs.length === 0 ? (
                    <p className="mt-2 text-xs text-muted">No runs yet</p>
                  ) : (
                    <ul className="mt-2 space-y-1">
                      {runs.slice(0, 5).map((run) => (
                        <li key={run.id} className="flex items-center justify-between text-xs text-slate-600">
                          <span
                            className={
                              run.status === "completed"
                                ? "text-teal-700"
                                : run.status === "failed"
                                  ? "text-red-600"
                                  : "text-amber-600"
                            }
                          >
                            {run.status}
                          </span>
                          <span>{timeAgo(run.completed_at)}</span>
                          {run.artifact_url && (
                            <a
                              href={run.artifact_url}
                              className="font-medium text-accent hover:underline"
                              download
                            >
                              Download
                            </a>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          ))}
        </section>
      )}
    </AppShell>
  );
}
