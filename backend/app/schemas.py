from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

RoleName = Literal["owner", "admin", "analyst", "viewer"]


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SignupRequest(APIModel):
    organization_name: str = Field(min_length=2, max_length=160)
    organization_slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$")
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(APIModel):
    email: EmailStr
    password: str
    organization_slug: str | None = None


class OrganizationRead(APIModel):
    id: str
    name: str
    slug: str
    retention_days: int
    feature_flags: dict[str, Any]


class UserRead(APIModel):
    id: str
    organization_id: str
    email: EmailStr
    full_name: str
    role: RoleName
    is_active: bool


class TokenPair(APIModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class InviteCreate(APIModel):
    email: EmailStr
    role: RoleName = "viewer"


class InviteAccept(APIModel):
    token: str
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=8, max_length=128)


class InviteRead(APIModel):
    id: str
    email: EmailStr
    role: RoleName
    expires_at: datetime
    accepted_at: datetime | None
    token: str | None = None


class ApiKeyCreate(APIModel):
    name: str = Field(min_length=2, max_length=120)
    scopes: list[str] = Field(default_factory=lambda: ["ingest:write"])


class ApiKeyRead(APIModel):
    id: str
    name: str
    prefix: str
    scopes: list[str]
    revoked_at: datetime | None
    last_used_at: datetime | None
    key: str | None = None


class EventIn(APIModel):
    event_type: str = Field(min_length=1, max_length=120)
    user_external_id: str | None = Field(default=None, max_length=160)
    occurred_at: datetime | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, max_length=128)
    source: str | None = Field(default=None, max_length=120)


class BatchEventsIn(APIModel):
    events: list[EventIn] = Field(min_length=1, max_length=1000)


class EventRead(APIModel):
    id: str
    event_type: str
    user_external_id: str | None
    occurred_at: datetime
    received_at: datetime
    properties: dict[str, Any]
    processed: bool


class SavedQueryCreate(APIModel):
    name: str
    metric: str = "count"
    event_type: str | None = None
    aggregation: str = "count"
    time_bucket: str = "hour"
    filters: dict[str, Any] = Field(default_factory=dict)


class SavedQueryRead(SavedQueryCreate):
    id: str
    organization_id: str


class WidgetCreate(APIModel):
    title: str
    type: Literal["line", "bar", "pie", "kpi", "table"]
    saved_query_id: str | None = None
    time_range: str = "24h"
    layout: dict[str, Any] = Field(default_factory=lambda: {"x": 0, "y": 0, "w": 4, "h": 3})
    options: dict[str, Any] = Field(default_factory=dict)


class WidgetRead(WidgetCreate):
    id: str
    dashboard_id: str


class DashboardCreate(APIModel):
    name: str = Field(min_length=2, max_length=160)
    description: str = ""
    visibility: Literal["team", "public"] = "team"
    auto_refresh_seconds: int = Field(default=60, ge=30, le=3600)


class DashboardRead(DashboardCreate):
    id: str
    organization_id: str
    owner_id: str
    public_token: str | None
    widgets: list[WidgetRead] = Field(default_factory=list)


class AlertRuleCreate(APIModel):
    name: str
    metric: Literal["event_count", "unique_users", "error_rate"] = "event_count"
    event_type: str | None = None
    saved_query_id: str | None = None
    operator: Literal[">", ">=", "<", "<=", "=="] = ">"
    threshold: float
    window_seconds: int = Field(default=600, ge=60)
    channels: list[Literal["in_app", "email", "webhook"]] = Field(default_factory=lambda: ["in_app"])
    email_recipients: list[EmailStr] = Field(default_factory=list)
    webhook_url: str | None = None


class AlertRuleRead(AlertRuleCreate):
    id: str
    organization_id: str
    status: Literal["active", "triggered", "resolved", "muted"]
    muted_until: datetime | None
    last_evaluated_at: datetime | None
    email_recipients: list[EmailStr] = Field(default_factory=list)
    webhook_url: str | None = None


class AlertEventRead(APIModel):
    id: str
    alert_rule_id: str
    status: str
    value: float
    message: str
    created_at: datetime


class ReportScheduleCreate(APIModel):
    dashboard_id: str | None = None
    name: str
    cron: str = "0 9 * * 1"
    recipients: list[EmailStr] = Field(default_factory=list)
    format: Literal["pdf", "png"] = "pdf"


class ReportScheduleRead(ReportScheduleCreate):
    id: str
    organization_id: str
    is_active: bool
    last_run_at: datetime | None


class ReportRunRead(APIModel):
    id: str
    schedule_id: str
    status: str
    artifact_url: str | None
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None


class MetricPoint(APIModel):
    bucket: datetime
    value: float


class QueryResult(APIModel):
    query_id: str | None
    total: float
    series: list[MetricPoint]


class WebhookDeliveryRead(APIModel):
    id: str
    target_url: str
    event_type: str
    status: str
    attempts: int
    next_attempt_at: datetime | None


class FeatureFlagsUpdate(APIModel):
    feature_flags: dict[str, bool]


class RetentionPolicyUpdate(APIModel):
    retention_days: int = Field(ge=1, le=3650)


class SqlSandboxRequest(APIModel):
    sql: str = Field(min_length=6, max_length=4000)
    limit: int = Field(default=100, ge=1, le=500)


class SqlSandboxResponse(APIModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    plan: list[str]


class WebhookDeliveryCreate(APIModel):
    target_url: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
