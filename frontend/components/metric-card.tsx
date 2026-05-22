import clsx from "clsx";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

import type { DashboardMetric } from "@/lib/types";

const toneClass = {
  good: "text-accent",
  warning: "text-warning",
  danger: "text-danger",
  neutral: "text-muted"
};

export function MetricCard({ metric }: { metric: DashboardMetric }) {
  const Icon = metric.change.startsWith("+") ? ArrowUpRight : metric.change.startsWith("-") ? ArrowDownRight : Minus;

  return (
    <div className="rounded border border-line bg-white p-4 shadow-soft">
      <div className="text-sm text-muted">{metric.label}</div>
      <div className="mt-2 flex items-end justify-between gap-3">
        <div className="text-2xl font-semibold tracking-normal">{metric.value}</div>
        <div className={clsx("flex items-center gap-1 text-sm font-medium", toneClass[metric.tone])}>
          <Icon size={15} aria-hidden />
          {metric.change}
        </div>
      </div>
    </div>
  );
}

