"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { AppShell } from "@/components/app-shell";
import { EventVolumeChart, SourceMixChart, TopSourcesChart } from "@/components/chart-panel";
import { EventTable } from "@/components/event-table";
import { MetricCard } from "@/components/metric-card";
import { getDashboardMetrics } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type { DashboardMetric } from "@/lib/types";

function formatNum(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}

function pctLabel(n: number): string {
  return n >= 0 ? `+${n}%` : `${n}%`;
}

export default function OverviewPage() {
  const router = useRouter();
  const { accessToken } = useAppStore();

  useEffect(() => {
    if (!accessToken) router.replace("/login" as never);
  }, [accessToken, router]);

  const { data: liveMetrics } = useQuery({
    queryKey: ["metrics", accessToken],
    queryFn: () => getDashboardMetrics(accessToken!),
    enabled: !!accessToken,
    refetchInterval: 60_000
  });

  const metrics: DashboardMetric[] = liveMetrics
    ? [
        {
          label: "Events today",
          value: formatNum(liveMetrics.events_today),
          change: pctLabel(liveMetrics.events_change_pct),
          tone: liveMetrics.events_change_pct >= 0 ? "good" : "warning"
        },
        {
          label: "Active users",
          value: formatNum(liveMetrics.active_users),
          change: pctLabel(liveMetrics.users_change_pct),
          tone: liveMetrics.users_change_pct >= 0 ? "good" : "warning"
        },
        {
          label: "Error rate",
          value: `${liveMetrics.error_rate_pct}%`,
          change: `${liveMetrics.errors_today} errors`,
          tone: liveMetrics.error_rate_pct > 5 ? "danger" : liveMetrics.error_rate_pct > 2 ? "warning" : "good"
        },
        {
          label: "Total events (24h)",
          value: formatNum(liveMetrics.events_today),
          change: "live",
          tone: "neutral"
        }
      ]
    : [0, 1, 2, 3].map((i) => ({ label: `loading-${i}`, value: "…", change: "", tone: "neutral" as const }));

  return (
    <AppShell>
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Executive Overview</h1>
          <p className="mt-1 text-sm text-muted">Live data · auto-refresh 60s · team access</p>
        </div>
        <div className="flex gap-2">
          <button className="focus-ring rounded border border-line bg-white px-3 py-2 text-sm font-medium hover:bg-slate-50">
            Share
          </button>
          <button className="focus-ring rounded bg-accent px-3 py-2 text-sm font-medium text-white hover:bg-teal-800">
            Add widget
          </button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => (
          <MetricCard key={metric.label} metric={metric} />
        ))}
      </div>

      <div className="mt-4">
        <EventVolumeChart />
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <SourceMixChart />
        <TopSourcesChart />
      </div>

      <div className="mt-4">
        <EventTable />
      </div>
    </AppShell>
  );
}
