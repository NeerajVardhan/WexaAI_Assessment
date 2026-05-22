from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base


def uuid() -> str:
    return str(uuid4())


json_type = JSON().with_variant(JSONB, "postgresql")


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    retention_days: Mapped[int] = mapped_column(Integer, default=365)
    feature_flags: Mapped[dict] = mapped_column(json_type, default=dict)

    users: Mapped[list["User"]] = relationship(back_populates="organization")


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("organization_id", "email", name="uq_user_org_email"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(24), nullable=False, default="viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped[Organization] = relationship(back_populates="users")


class Invite(TimestampMixin, Base):
    __tablename__ = "invites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    invited_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RefreshToken(TimestampMixin, Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApiKey(TimestampMixin, Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    prefix: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    scopes: Mapped[list[str]] = mapped_column(json_type, default=list)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DataSource(TimestampMixin, Base):
    __tablename__ = "data_sources"
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_source_org_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    config: Mapped[dict] = mapped_column(json_type, default=dict)


class Event(TimestampMixin, Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_org_type_time", "organization_id", "event_type", "occurred_at"),
        Index("ix_events_org_received", "organization_id", "received_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("data_sources.id"), nullable=True)
    api_key_id: Mapped[str | None] = mapped_column(ForeignKey("api_keys.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    user_external_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    properties: Mapped[dict] = mapped_column(json_type, default=dict)
    raw: Mapped[dict] = mapped_column(json_type, default=dict)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class SavedQuery(TimestampMixin, Base):
    __tablename__ = "saved_queries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    metric: Mapped[str] = mapped_column(String(80), nullable=False, default="count")
    event_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    aggregation: Mapped[str] = mapped_column(String(32), nullable=False, default="count")
    time_bucket: Mapped[str] = mapped_column(String(32), nullable=False, default="hour")
    filters: Mapped[dict] = mapped_column(json_type, default=dict)


class Dashboard(TimestampMixin, Base):
    __tablename__ = "dashboards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    visibility: Mapped[str] = mapped_column(String(24), default="team")
    public_token: Mapped[str | None] = mapped_column(String(80), unique=True, nullable=True)
    auto_refresh_seconds: Mapped[int] = mapped_column(Integer, default=60)

    widgets: Mapped[list["Widget"]] = relationship(cascade="all, delete-orphan")


class Widget(TimestampMixin, Base):
    __tablename__ = "widgets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    dashboard_id: Mapped[str] = mapped_column(ForeignKey("dashboards.id"), index=True)
    saved_query_id: Mapped[str | None] = mapped_column(ForeignKey("saved_queries.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    time_range: Mapped[str] = mapped_column(String(40), default="24h")
    layout: Mapped[dict] = mapped_column(json_type, default=dict)
    options: Mapped[dict] = mapped_column(json_type, default=dict)


class AlertRule(TimestampMixin, Base):
    __tablename__ = "alert_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    saved_query_id: Mapped[str | None] = mapped_column(ForeignKey("saved_queries.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    metric: Mapped[str] = mapped_column(String(80), nullable=False, default="event_count")
    event_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    operator: Mapped[str] = mapped_column(String(8), default=">")
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    window_seconds: Mapped[int] = mapped_column(Integer, default=600)
    channels: Mapped[list[str]] = mapped_column(json_type, default=list)
    email_recipients: Mapped[list[str]] = mapped_column(json_type, default=list)
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="active")
    muted_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AlertEvent(TimestampMixin, Base):
    __tablename__ = "alert_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    alert_rule_id: Mapped[str] = mapped_column(ForeignKey("alert_rules.id"), index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    message: Mapped[str] = mapped_column(Text, default="")


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(json_type, default=dict)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReportSchedule(TimestampMixin, Base):
    __tablename__ = "report_schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    dashboard_id: Mapped[str | None] = mapped_column(ForeignKey("dashboards.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    cron: Mapped[str] = mapped_column(String(120), nullable=False)
    recipients: Mapped[list[str]] = mapped_column(json_type, default=list)
    format: Mapped[str] = mapped_column(String(16), default="pdf")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReportRun(TimestampMixin, Base):
    __tablename__ = "report_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    schedule_id: Mapped[str] = mapped_column(ForeignKey("report_schedules.id"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="queued")
    artifact_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WebhookDelivery(TimestampMixin, Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    target_url: Mapped[str] = mapped_column(String(500), nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict] = mapped_column(json_type, default=dict)
    status: Mapped[str] = mapped_column(String(24), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

