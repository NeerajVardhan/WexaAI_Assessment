"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BellRing, CheckCircle2, Clock, Loader2, Pause, Play, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { StatusPill } from "@/components/status-pill";
import { createAlert, evaluateAlert, listAlerts, muteAlert } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type { AlertRuleCreate } from "@/lib/types";

function timeAgo(raw: string | null | undefined) {
  if (!raw) return "Never";
  const diff = Date.now() - new Date(raw).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  return `${Math.floor(mins / 60)}h ago`;
}

const METRIC_LABELS: Record<string, string> = {
  event_count: "Event count",
  unique_users: "Unique users",
  error_rate: "Error rate (%)"
};

const DEFAULT_FORM: AlertRuleCreate = {
  name: "",
  metric: "event_count",
  event_type: null,
  operator: ">",
  threshold: 100,
  window_seconds: 600,
  channels: ["in_app"],
  email_recipients: [],
  webhook_url: null
};

export default function AlertsPage() {
  const router = useRouter();
  const { accessToken } = useAppStore();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<AlertRuleCreate>(DEFAULT_FORM);
  const [recipientsRaw, setRecipientsRaw] = useState("");

  useEffect(() => {
    if (!accessToken) router.replace("/login" as never);
  }, [accessToken, router]);

  const { data: alerts = [], isLoading } = useQuery({
    queryKey: ["alerts", accessToken],
    queryFn: () => listAlerts(accessToken!),
    enabled: !!accessToken,
    refetchInterval: 30_000
  });

  const createMut = useMutation({
    mutationFn: () =>
      createAlert(accessToken!, {
        ...form,
        email_recipients: recipientsRaw
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean)
      }),
    onSuccess: () => {
      setShowForm(false);
      setForm(DEFAULT_FORM);
      setRecipientsRaw("");
      qc.invalidateQueries({ queryKey: ["alerts"] });
    }
  });

  const evalMut = useMutation({
    mutationFn: (ruleId: string) => evaluateAlert(accessToken!, ruleId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] })
  });

  const muteMut = useMutation({
    mutationFn: (ruleId: string) => muteAlert(accessToken!, ruleId, 60),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] })
  });

  const triggered = alerts.filter((a) => a.status === "triggered").length;
  const active = alerts.filter((a) => a.status === "active").length;
  const muted = alerts.filter((a) => a.status === "muted").length;

  return (
    <AppShell>
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Alerts</h1>
          <p className="mt-1 text-sm text-muted">Threshold rules, notification channels, evaluation history</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="focus-ring inline-flex items-center gap-2 rounded bg-accent px-3 py-2 text-sm font-medium text-white hover:bg-teal-800"
        >
          <BellRing size={16} aria-hidden />
          New alert
        </button>
      </div>

      {showForm && (
        <div className="mb-4 rounded border border-line bg-white p-5 shadow-soft">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold">New alert rule</h2>
            <button onClick={() => setShowForm(false)} className="text-muted hover:text-ink">
              <X size={16} />
            </button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium">Rule name</label>
              <input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                className="focus-ring h-9 w-full rounded border border-line bg-slate-50 px-3 text-sm"
                placeholder="Error rate spike"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Metric</label>
              <select
                value={form.metric}
                onChange={(e) => setForm((f) => ({ ...f, metric: e.target.value as AlertRuleCreate["metric"] }))}
                className="focus-ring h-9 w-full rounded border border-line bg-slate-50 px-2 text-sm"
              >
                {Object.entries(METRIC_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">
                Event type filter <span className="font-normal text-muted">(optional)</span>
              </label>
              <input
                value={form.event_type ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, event_type: e.target.value || null }))}
                className="focus-ring h-9 w-full rounded border border-line bg-slate-50 px-3 text-sm"
                placeholder="e.g. page_view, error, click"
              />
            </div>
            <div className="flex gap-2">
              <div className="w-28">
                <label className="mb-1 block text-sm font-medium">Operator</label>
                <select
                  value={form.operator}
                  onChange={(e) => setForm((f) => ({ ...f, operator: e.target.value as AlertRuleCreate["operator"] }))}
                  className="focus-ring h-9 w-full rounded border border-line bg-slate-50 px-2 text-sm"
                >
                  {[">", ">=", "<", "<=", "=="].map((op) => (
                    <option key={op}>{op}</option>
                  ))}
                </select>
              </div>
              <div className="flex-1">
                <label className="mb-1 block text-sm font-medium">Threshold</label>
                <input
                  type="number"
                  value={form.threshold}
                  onChange={(e) => setForm((f) => ({ ...f, threshold: Number(e.target.value) }))}
                  className="focus-ring h-9 w-full rounded border border-line bg-slate-50 px-3 text-sm"
                />
              </div>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Window (seconds)</label>
              <input
                type="number"
                value={form.window_seconds}
                onChange={(e) => setForm((f) => ({ ...f, window_seconds: Number(e.target.value) }))}
                className="focus-ring h-9 w-full rounded border border-line bg-slate-50 px-3 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Email recipients (comma-separated)</label>
              <input
                value={recipientsRaw}
                onChange={(e) => setRecipientsRaw(e.target.value)}
                className="focus-ring h-9 w-full rounded border border-line bg-slate-50 px-3 text-sm"
                placeholder="team@example.com"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="mb-1 block text-sm font-medium">Channels</label>
              <div className="flex gap-4">
                {["in_app", "email", "webhook"].map((ch) => (
                  <label key={ch} className="flex cursor-pointer items-center gap-1.5 text-sm">
                    <input
                      type="checkbox"
                      checked={form.channels?.includes(ch)}
                      onChange={(e) =>
                        setForm((f) => ({
                          ...f,
                          channels: e.target.checked
                            ? [...(f.channels ?? []), ch]
                            : (f.channels ?? []).filter((c) => c !== ch)
                        }))
                      }
                    />
                    {ch}
                  </label>
                ))}
              </div>
            </div>
          </div>
          <button
            onClick={() => createMut.mutate()}
            disabled={!form.name || createMut.isPending}
            className="focus-ring mt-4 rounded bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-50"
          >
            {createMut.isPending ? "Creating…" : "Create rule"}
          </button>
        </div>
      )}

      <section className="rounded border border-line bg-white shadow-soft">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Rule</th>
                <th className="px-4 py-3 font-medium">Metric</th>
                <th className="px-4 py-3 font-medium">Condition</th>
                <th className="px-4 py-3 font-medium">Channels</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Evaluated</th>
                <th className="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-sm text-muted">
                    <Loader2 size={16} className="mx-auto animate-spin" />
                  </td>
                </tr>
              ) : alerts.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-sm text-muted">
                    No alert rules. Click "New alert" to create one.
                  </td>
                </tr>
              ) : (
                alerts.map((alert) => (
                  <tr key={alert.id}>
                    <td className="px-4 py-3 font-medium">
                      {alert.name}
                      {alert.event_type && (
                        <span className="ml-1.5 rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500">
                          {alert.event_type}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{METRIC_LABELS[alert.metric] ?? alert.metric}</td>
                    <td className="px-4 py-3 text-slate-600">
                      {alert.operator} {alert.threshold}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{alert.channels.join(", ")}</td>
                    <td className="px-4 py-3">
                      <StatusPill value={alert.status} />
                    </td>
                    <td className="px-4 py-3 text-slate-600">{timeAgo(alert.last_evaluated_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button
                          onClick={() => evalMut.mutate(alert.id)}
                          disabled={evalMut.isPending}
                          className="focus-ring inline-flex h-8 w-8 items-center justify-center rounded border border-line hover:bg-slate-50 disabled:opacity-50"
                          title="Evaluate now"
                        >
                          <Play size={14} />
                        </button>
                        <button
                          onClick={() => muteMut.mutate(alert.id)}
                          disabled={muteMut.isPending || alert.status === "muted"}
                          className="focus-ring inline-flex h-8 w-8 items-center justify-center rounded border border-line hover:bg-slate-50 disabled:opacity-50"
                          title="Mute 60 min"
                        >
                          <Pause size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-4 grid gap-4 lg:grid-cols-3">
        {[
          { label: "Triggered", count: triggered, icon: BellRing, tone: "text-red-600" },
          { label: "Active rules", count: active, icon: CheckCircle2, tone: "text-teal-600" },
          { label: "Muted", count: muted, icon: Clock, tone: "text-amber-600" }
        ].map(({ label, count, icon: Icon, tone }) => (
          <div key={label} className="rounded border border-line bg-white p-4 shadow-soft">
            <Icon size={18} className={tone} aria-hidden />
            <h2 className="mt-3 font-semibold">{label}</h2>
            <p className="mt-1 text-2xl font-bold">{count}</p>
          </div>
        ))}
      </section>
    </AppShell>
  );
}
