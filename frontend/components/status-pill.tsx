import clsx from "clsx";

type Props = {
  value: string;
};

export function StatusPill({ value }: Props) {
  return (
    <span
      className={clsx(
        "inline-flex h-6 items-center rounded px-2 text-xs font-medium capitalize",
        value === "triggered" && "bg-red-50 text-danger ring-1 ring-red-200",
        value === "active" && "bg-teal-50 text-accent ring-1 ring-teal-200",
        value === "resolved" && "bg-slate-100 text-slate-700 ring-1 ring-slate-200",
        value === "muted" && "bg-amber-50 text-warning ring-1 ring-amber-200"
      )}
    >
      {value}
    </span>
  );
}

