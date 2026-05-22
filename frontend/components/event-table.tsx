"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Clock3, Wifi, WifiOff } from "lucide-react";
import { useCallback } from "react";

import { listRecentEvents } from "@/lib/api";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useAppStore } from "@/lib/store";
import type { EventRecord } from "@/lib/types";

function timeAgo(raw: string) {
  const diff = Date.now() - new Date(raw).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  return `${Math.floor(mins / 60)}h ago`;
}

export function EventTable() {
  const { accessToken, organizationId } = useAppStore();
  const qc = useQueryClient();

  const { data: events = [], isLoading } = useQuery({
    queryKey: ["live-events", accessToken],
    queryFn: () => listRecentEvents(accessToken!, 30),
    enabled: !!accessToken,
    refetchInterval: 30_000
  });

  const handleWsMessage = useCallback(
    (msg: Record<string, unknown>) => {
      if (msg.type === "event.ingested" || msg.type === "client_ping") {
        qc.invalidateQueries({ queryKey: ["live-events"] });
      }
    },
    [qc]
  );

  const { connected } = useWebSocket({
    organizationId,
    path: "events",
    onMessage: handleWsMessage,
    enabled: !!accessToken && !!organizationId
  });

  return (
    <section className="rounded border border-line bg-white shadow-soft">
      <div className="flex h-12 items-center justify-between border-b border-line px-4">
        <h2 className="text-base font-semibold">Live event stream</h2>
        <div className="flex items-center gap-2 text-sm text-muted">
          {connected ? (
            <>
              <Wifi size={14} className="text-teal-600" aria-hidden />
              <span className="text-teal-600">live</span>
            </>
          ) : (
            <>
              <WifiOff size={14} className="text-amber-500" aria-hidden />
              <span className="text-amber-500">reconnecting</span>
            </>
          )}
          <Clock3 size={14} aria-hidden />
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[680px] text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-muted">
            <tr>
              <th className="px-4 py-3 font-medium">Event</th>
              <th className="px-4 py-3 font-medium">User</th>
              <th className="px-4 py-3 font-medium">Properties</th>
              <th className="px-4 py-3 font-medium">Received</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {isLoading ? (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-muted">
                  Loading…
                </td>
              </tr>
            ) : (events as EventRecord[]).length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-muted">
                  No events yet — start ingesting data.
                </td>
              </tr>
            ) : (
              (events as EventRecord[]).map((event) => (
                <tr key={event.id}>
                  <td className="px-4 py-3 font-medium text-ink">{event.event_type}</td>
                  <td className="px-4 py-3 text-slate-600">{event.user_external_id ?? "—"}</td>
                  <td className="px-4 py-3 text-slate-600">
                    {Object.entries(event.properties)
                      .slice(0, 3)
                      .map(([k, v]) => `${k}: ${v}`)
                      .join(" · ")}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{timeAgo(event.received_at)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
