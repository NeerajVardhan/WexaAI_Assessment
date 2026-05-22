import type {
  AlertRule,
  AlertRuleCreate,
  ApiKey,
  Dashboard,
  EventRecord,
  LiveMetrics,
  QueryResult,
  ReportRun,
  ReportSchedule,
  SourceItem,
  TokenPair
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export async function apiFetch<T>(path: string, token?: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type") && !(init?.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    credentials: "include",
    cache: "no-store"
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? body?.error?.message ?? `Request failed with ${response.status}`);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function websocketUrl(path: string): string {
  const base = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/api/v1/ws";
  return `${base}${path}`;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export function login(email: string, password: string, org?: string) {
  return apiFetch<TokenPair>("/auth/login", undefined, {
    method: "POST",
    body: JSON.stringify({ email, password, organization_slug: org ?? null })
  });
}

export function signup(payload: {
  organization_name: string;
  organization_slug: string;
  full_name: string;
  email: string;
  password: string;
}) {
  return apiFetch<TokenPair>("/auth/signup", undefined, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function logout(token: string) {
  return apiFetch<void>("/auth/logout", token, { method: "POST" });
}

export function getMe(token: string) {
  return apiFetch<TokenPair["user"]>("/auth/me", token);
}

// ── API Keys ──────────────────────────────────────────────────────────────────

export function listApiKeys(token: string) {
  return apiFetch<ApiKey[]>("/api-keys", token);
}

export function createApiKey(token: string, name: string, scopes?: string[]) {
  return apiFetch<ApiKey & { key: string }>("/api-keys", token, {
    method: "POST",
    body: JSON.stringify({ name, scopes: scopes ?? ["ingest:write"] })
  });
}

export function revokeApiKey(token: string, keyId: string) {
  return apiFetch<ApiKey>(`/api-keys/${keyId}/revoke`, token, { method: "POST" });
}

export function rotateApiKey(token: string, keyId: string) {
  return apiFetch<{ key: ApiKey; raw: string }>(`/api-keys/${keyId}/rotate`, token, { method: "POST" });
}

// ── Ingestion ─────────────────────────────────────────────────────────────────

export function listRecentEvents(token: string, limit = 50) {
  return apiFetch<EventRecord[]>(`/ingest/events?limit=${limit}`, token);
}

export function ingestEvent(token: string, payload: Record<string, unknown>) {
  return apiFetch<{ id: string }>("/ingest/event", token, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function ingestCsv(token: string, file: File) {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<{ accepted: number }>("/ingest/csv", token, { method: "POST", body: form });
}

// ── Dashboards ────────────────────────────────────────────────────────────────

export function listDashboards(token: string) {
  return apiFetch<Dashboard[]>("/dashboards", token);
}

export function getDashboardMetrics(token: string) {
  return apiFetch<LiveMetrics>("/dashboards/metrics", token);
}

export function getSourceBreakdown(token: string) {
  return apiFetch<SourceItem[]>("/dashboards/sources", token);
}

export function runQuery(token: string, queryId?: string, hours = 24) {
  const qs = new URLSearchParams({ hours: String(hours) });
  if (queryId) qs.set("query_id", queryId);
  return apiFetch<QueryResult>(`/dashboards/queries/run?${qs}`, token);
}

export function listTemplates() {
  return apiFetch<Array<{ key: string; name: string; description: string }>>("/dashboards/templates");
}

// ── Alerts ───────────────────────────────────────────────────────────────────

export function listAlerts(token: string) {
  return apiFetch<AlertRule[]>("/alerts", token);
}

export function createAlert(token: string, payload: AlertRuleCreate) {
  return apiFetch<AlertRule>("/alerts", token, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function evaluateAlert(token: string, ruleId: string) {
  return apiFetch<{ id: string; status: string; value: number }>(`/alerts/${ruleId}/evaluate`, token, {
    method: "POST"
  });
}

export function muteAlert(token: string, ruleId: string, minutes = 60) {
  return apiFetch<AlertRule>(`/alerts/${ruleId}/mute`, token, {
    method: "POST",
    body: JSON.stringify({ minutes })
  });
}

// ── Reports ───────────────────────────────────────────────────────────────────

export function listReports(token: string) {
  return apiFetch<ReportSchedule[]>("/reports", token);
}

export function createReport(
  token: string,
  payload: { dashboard_id: string | null; name: string; cron: string; recipients: string[]; format: "pdf" | "png" }
) {
  return apiFetch<ReportSchedule>("/reports", token, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function runReport(token: string, scheduleId: string) {
  return apiFetch<ReportRun>(`/reports/${scheduleId}/run`, token, { method: "POST" });
}

export function listReportRuns(token: string, scheduleId: string) {
  return apiFetch<ReportRun[]>(`/reports/${scheduleId}/runs`, token);
}
