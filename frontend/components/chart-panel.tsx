"use client";

import { useQuery } from "@tanstack/react-query";
import { BarChart3, Maximize2, Minimize2, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import { getSourceBreakdown, runQuery } from "@/lib/api";
import { useAppStore } from "@/lib/store";

const COLORS = ["#0f766e", "#b45309", "#6366f1", "#f59e0b", "#334155", "#ec4899"];

function formatBucket(raw: string) {
  try {
    return new Date(raw).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return raw;
  }
}

function ChartHeader({
  title,
  subtitle,
  isLoading,
  actions
}: {
  title: string;
  subtitle?: string;
  isLoading?: boolean;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-5 flex items-start justify-between gap-3">
      <div>
        <h2 className="text-base font-semibold leading-tight">{title}</h2>
        {subtitle && <p className="mt-0.5 text-xs text-muted">{subtitle}</p>}
        {isLoading && <span className="mt-0.5 block text-xs text-muted">Refreshing…</span>}
      </div>
      {actions && <div className="flex shrink-0 gap-1.5">{actions}</div>}
    </div>
  );
}

export function EventVolumeChart() {
  const { accessToken } = useAppStore();
  const [fullscreen, setFullscreen] = useState(false);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["event-series", accessToken],
    queryFn: () => runQuery(accessToken!, undefined, 24),
    enabled: !!accessToken,
    refetchInterval: 60_000
  });

  const chartData = (data?.series ?? []).map((p) => ({
    bucket: formatBucket(p.bucket),
    value: p.value
  }));

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setFullscreen(false);
    }
    if (fullscreen) window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [fullscreen]);

  return (
    <section
      className={
        fullscreen
          ? "fixed inset-0 z-50 flex flex-col bg-white p-8 shadow-2xl"
          : "rounded-lg border border-line bg-white p-6 shadow-soft"
      }
    >
      <ChartHeader
        title="Event volume"
        subtitle="Hourly count over the last 24 hours"
        isLoading={isLoading}
        actions={
          <>
            <button
              onClick={() => refetch()}
              className="focus-ring inline-flex h-8 w-8 items-center justify-center rounded border border-line hover:bg-slate-50"
              title="Refresh"
            >
              <RefreshCw size={14} aria-label="Refresh" />
            </button>
            <button
              onClick={() => setFullscreen((f) => !f)}
              className="focus-ring inline-flex h-8 w-8 items-center justify-center rounded border border-line hover:bg-slate-50"
              title={fullscreen ? "Exit fullscreen" : "Fullscreen"}
            >
              {fullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            </button>
          </>
        }
      />

      {chartData.length === 0 && !isLoading ? (
        <div className="flex h-64 flex-col items-center justify-center gap-2">
          <BarChart3 size={32} className="text-slate-200" />
          <p className="text-sm text-muted">No events in the last 24 hours</p>
        </div>
      ) : (
        <div className={fullscreen ? "flex-1" : "h-72"}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ left: 0, right: 16, top: 8, bottom: 0 }}>
              <defs>
                <linearGradient id="eventFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0f766e" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#0f766e" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#f1f5f9" vertical={false} />
              <XAxis
                dataKey="bucket"
                tickLine={false}
                axisLine={false}
                fontSize={11}
                tick={{ fill: "#94a3b8" }}
                interval="preserveStartEnd"
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                fontSize={11}
                tick={{ fill: "#94a3b8" }}
                width={36}
                allowDecimals={false}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: "8px",
                  border: "1px solid #e2e8f0",
                  boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.07)",
                  fontSize: "12px"
                }}
                labelStyle={{ fontWeight: 600, marginBottom: 2 }}
                cursor={{ stroke: "#0f766e", strokeWidth: 1, strokeDasharray: "4 2" }}
              />
              <Area
                type="monotone"
                dataKey="value"
                name="Events"
                stroke="#0f766e"
                fill="url(#eventFill)"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: "#0f766e", stroke: "#fff", strokeWidth: 2 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}

export function SourceMixChart() {
  const { accessToken } = useAppStore();

  const { data: sources, isLoading } = useQuery({
    queryKey: ["sources", accessToken],
    queryFn: () => getSourceBreakdown(accessToken!),
    enabled: !!accessToken,
    refetchInterval: 60_000
  });

  const sourceData = sources ?? [];

  return (
    <section className="rounded-lg border border-line bg-white p-6 shadow-soft">
      <ChartHeader title="Source mix" subtitle="Traffic share by origin" isLoading={isLoading} />
      {isLoading ? (
        <div className="flex h-56 items-center justify-center text-sm text-muted">Loading…</div>
      ) : sourceData.length === 0 ? (
        <div className="flex h-56 items-center justify-center text-sm text-muted">No data yet</div>
      ) : (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={sourceData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="45%"
                innerRadius={52}
                outerRadius={80}
                paddingAngle={3}
              >
                {sourceData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(v) => [`${v}%`, "Share"]}
                contentStyle={{
                  borderRadius: "8px",
                  border: "1px solid #e2e8f0",
                  fontSize: "12px"
                }}
              />
              <Legend
                iconType="circle"
                iconSize={8}
                formatter={(value) => (
                  <span style={{ fontSize: 12, color: "#475569" }}>{value}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}

export function TopSourcesChart() {
  const { accessToken } = useAppStore();

  const { data: sources, isLoading } = useQuery({
    queryKey: ["sources", accessToken],
    queryFn: () => getSourceBreakdown(accessToken!),
    enabled: !!accessToken,
    refetchInterval: 60_000
  });

  const sourceData = sources ?? [];

  return (
    <section className="rounded-lg border border-line bg-white p-6 shadow-soft">
      <ChartHeader title="Top sources" subtitle="Event share by source name" isLoading={isLoading} />
      {isLoading ? (
        <div className="flex h-56 items-center justify-center text-sm text-muted">Loading…</div>
      ) : sourceData.length === 0 ? (
        <div className="flex h-56 items-center justify-center text-sm text-muted">No data yet</div>
      ) : (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={sourceData}
              layout="vertical"
              margin={{ left: 8, right: 24, top: 4, bottom: 4 }}
            >
              <CartesianGrid stroke="#f1f5f9" horizontal={false} />
              <XAxis
                type="number"
                tickLine={false}
                axisLine={false}
                fontSize={11}
                tick={{ fill: "#94a3b8" }}
                tickFormatter={(v) => `${v}%`}
              />
              <YAxis
                type="category"
                dataKey="name"
                tickLine={false}
                axisLine={false}
                fontSize={11}
                tick={{ fill: "#475569" }}
                width={64}
              />
              <Tooltip
                formatter={(v) => [`${v}%`, "Share"]}
                contentStyle={{
                  borderRadius: "8px",
                  border: "1px solid #e2e8f0",
                  fontSize: "12px"
                }}
                cursor={{ fill: "#f8fafc" }}
              />
              <Bar dataKey="value" fill="#b45309" radius={[0, 4, 4, 0]} barSize={18}>
                {sourceData.map((_, index) => (
                  <Cell key={`bar-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}

/** @deprecated use SourceMixChart + TopSourcesChart separately */
export function SourceCharts() {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <SourceMixChart />
      <TopSourcesChart />
    </div>
  );
}
