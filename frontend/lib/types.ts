export type RoleName = "owner" | "admin" | "analyst" | "viewer";

export type MetricPoint = {
  bucket: string;
  value: number;
};

export type DashboardMetric = {
  label: string;
  value: string;
  change: string;
  tone: "good" | "warning" | "danger" | "neutral";
};

export type EventRecord = {
  id: string;
  event_type: string;
  user_external_id?: string;
  received_at: string;
  occurred_at: string;
  properties: Record<string, string | number | boolean>;
  processed: boolean;
};

export type AlertMetric = "event_count" | "unique_users" | "error_rate";

export type AlertRule = {
  id: string;
  name: string;
  metric: AlertMetric;
  event_type?: string | null;
  status: "active" | "triggered" | "resolved" | "muted";
  threshold: number;
  operator: string;
  channels: string[];
  email_recipients: string[];
  webhook_url?: string | null;
  last_evaluated_at?: string | null;
  muted_until?: string | null;
  window_seconds: number;
};

export type AlertRuleCreate = {
  name: string;
  metric: AlertMetric;
  event_type?: string | null;
  operator: ">" | ">=" | "<" | "<=" | "==";
  threshold: number;
  window_seconds?: number;
  channels?: string[];
  email_recipients?: string[];
  webhook_url?: string | null;
};

export type ReportSchedule = {
  id: string;
  name: string;
  cron: string;
  format: "pdf" | "png";
  recipients: string[];
  is_active: boolean;
  last_run_at?: string | null;
  dashboard_id: string;
};

export type ReportRun = {
  id: string;
  schedule_id: string;
  status: string;
  artifact_url?: string | null;
  error?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
};

export type ApiKey = {
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  revoked_at?: string | null;
  last_used_at?: string | null;
};

export type Dashboard = {
  id: string;
  name: string;
  description: string;
  visibility: "team" | "public";
  public_token?: string | null;
  auto_refresh_seconds: number;
  widgets: Widget[];
};

export type Widget = {
  id: string;
  dashboard_id: string;
  title: string;
  type: "line" | "bar" | "pie" | "kpi" | "table";
  time_range: string;
  layout: Record<string, number>;
  options: Record<string, unknown>;
};

export type UserRead = {
  id: string;
  organization_id: string;
  email: string;
  full_name: string;
  role: RoleName;
  is_active: boolean;
};

export type TokenPair = {
  access_token: string;
  token_type: string;
  user: UserRead;
};

export type QueryResult = {
  query_id: string | null;
  total: number;
  series: MetricPoint[];
};

export type LiveMetrics = {
  events_today: number;
  events_change_pct: number;
  active_users: number;
  users_change_pct: number;
  error_rate_pct: number;
  errors_today: number;
};

export type SourceItem = { name: string; value: number };
