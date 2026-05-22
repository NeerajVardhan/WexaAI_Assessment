"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { websocketUrl } from "@/lib/api";

type WsMessage = Record<string, unknown>;

type Options = {
  organizationId: string;
  path: "events" | "notifications";
  onMessage?: (msg: WsMessage) => void;
  enabled?: boolean;
};

export function useWebSocket({ organizationId, path, onMessage, enabled = true }: Options) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [connected, setConnected] = useState(false);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (!enabled || !organizationId) return;
    const url = websocketUrl(`/${path}/${organizationId}`);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as WsMessage;
        onMessageRef.current?.(data);
      } catch {
        // ignore malformed frames
      }
    };

    ws.onclose = () => {
      setConnected(false);
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => ws.close();
  }, [enabled, organizationId, path]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { connected };
}
