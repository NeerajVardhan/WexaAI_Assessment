from __future__ import annotations

import csv
import io
import os
import secrets
from collections.abc import Iterable, Sequence
from datetime import timedelta
from io import StringIO

import httpx
from fpdf import FPDF
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import AuthenticationFailed, NotFound
from app.core.permissions import Role
from app.core.security import (
    create_access_token,
    hash_password,
    hash_secret,
    new_secret,
    utcnow,
    verify_password,
)
from app.models import (
    AlertEvent,
    AlertRule,
    ApiKey,
    Dashboard,
    DataSource,
    Event,
    Invite,
    Notification,
    Organization,
    RefreshToken,
    ReportRun,
    ReportSchedule,
    SavedQuery,
    User,
    WebhookDelivery,
    Widget,
)
from app.schemas import (
    AlertRuleCreate,
    ApiKeyCreate,
    BatchEventsIn,
    DashboardCreate,
    EventIn,
    InviteAccept,
    InviteCreate,
    LoginRequest,
    ReportScheduleCreate,
    SavedQueryCreate,
    SignupRequest,
    SqlSandboxRequest,
    WebhookDeliveryCreate,
    WidgetCreate,
)


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def signup(self, payload: SignupRequest) -> tuple[User, str]:
        exists = await self.session.scalar(
            select(Organization).where(Organization.slug == payload.organization_slug)
        )
        if exists:
            raise AuthenticationFailed("Organization slug is already in use", status_code=409)
        organization = Organization(name=payload.organization_name, slug=payload.organization_slug)
        self.session.add(organization)
        await self.session.flush()
        user = User(
            organization_id=organization.id,
            email=payload.email.lower(),
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            role=Role.OWNER.value,
        )
        self.session.add(user)
        await self.session.flush()
        refresh_token = await self._issue_refresh_token(user)
        await self.session.commit()
        return user, refresh_token

    async def login(self, payload: LoginRequest) -> tuple[User, str]:
        statement = select(User).join(Organization).where(User.email == payload.email.lower())
        if payload.organization_slug:
            statement = statement.where(Organization.slug == payload.organization_slug)
        user = (await self.session.execute(statement)).scalar_one_or_none()
        if user is None or not verify_password(payload.password, user.password_hash):
            raise AuthenticationFailed("Invalid email or password")
        if not user.is_active:
            raise AuthenticationFailed("User is inactive")
        user.last_login_at = utcnow()
        refresh_token = await self._issue_refresh_token(user)
        await self.session.commit()
        return user, refresh_token

    async def refresh(self, raw_refresh_token: str) -> User:
        token_hash = hash_secret(raw_refresh_token)
        token = await self.session.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > utcnow(),
            )
        )
        if token is None:
            raise AuthenticationFailed("Refresh token is invalid")
        user = await self.session.get(User, token.user_id)
        if user is None or not user.is_active:
            raise AuthenticationFailed("Refresh token user is invalid")
        return user

    async def create_invite(self, user: User, payload: InviteCreate) -> tuple[Invite, str]:
        raw_token = new_secret("invite")
        invite = Invite(
            organization_id=user.organization_id,
            email=payload.email.lower(),
            role=payload.role,
            token_hash=hash_secret(raw_token),
            invited_by_user_id=user.id,
            expires_at=utcnow() + timedelta(days=7),
        )
        self.session.add(invite)
        await self.session.commit()
        invite.token = raw_token  # type: ignore[attr-defined]
        return invite, raw_token

    async def accept_invite(self, payload: InviteAccept) -> tuple[User, str]:
        invite = await self.session.scalar(
            select(Invite).where(
                Invite.token_hash == hash_secret(payload.token),
                Invite.accepted_at.is_(None),
                Invite.expires_at > utcnow(),
            )
        )
        if invite is None:
            raise AuthenticationFailed("Invite is invalid or expired")
        existing = await self.session.scalar(
            select(User).where(User.organization_id == invite.organization_id, User.email == invite.email)
        )
        if existing is not None:
            raise AuthenticationFailed("Invite has already been claimed", status_code=409)
        user = User(
            organization_id=invite.organization_id,
            email=invite.email,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            role=invite.role,
        )
        invite.accepted_at = utcnow()
        self.session.add(user)
        await self.session.flush()
        refresh_token = await self._issue_refresh_token(user)
        await self.session.commit()
        return user, refresh_token

    async def _issue_refresh_token(self, user: User) -> str:
        raw = new_secret("refresh")
        token = RefreshToken(
            user_id=user.id,
            token_hash=hash_secret(raw),
            expires_at=utcnow() + timedelta(days=settings.refresh_token_expire_days),
        )
        self.session.add(token)
        return raw

    @staticmethod
    def access_token_for(user: User) -> str:
        return create_access_token(user.id, user.organization_id, user.role)


class ApiKeyService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user: User, payload: ApiKeyCreate) -> tuple[ApiKey, str]:
        raw = new_secret("wx_live")
        key = ApiKey(
            organization_id=user.organization_id,
            name=payload.name,
            prefix=raw[:14],
            key_hash=hash_secret(raw),
            scopes=payload.scopes,
        )
        self.session.add(key)
        await self.session.commit()
        return key, raw

    async def list(self, organization_id: str) -> Sequence[ApiKey]:
        return (
            await self.session.execute(
                select(ApiKey)
                .where(ApiKey.organization_id == organization_id)
                .order_by(ApiKey.created_at.desc())
            )
        ).scalars().all()

    async def revoke(self, organization_id: str, key_id: str) -> ApiKey:
        key = await self._get(organization_id, key_id)
        key.revoked_at = utcnow()
        await self.session.commit()
        return key

    async def rotate(self, organization_id: str, key_id: str) -> tuple[ApiKey, str]:
        old = await self._get(organization_id, key_id)
        old.revoked_at = utcnow()
        raw = new_secret("wx_live")
        key = ApiKey(
            organization_id=organization_id,
            name=f"{old.name} rotated",
            prefix=raw[:14],
            key_hash=hash_secret(raw),
            scopes=old.scopes,
        )
        self.session.add(key)
        await self.session.commit()
        return key, raw

    async def authenticate(self, raw_api_key: str) -> ApiKey:
        key = await self.session.scalar(
            select(ApiKey).where(ApiKey.key_hash == hash_secret(raw_api_key), ApiKey.revoked_at.is_(None))
        )
        if key is None:
            raise AuthenticationFailed("Invalid API key")
        key.last_used_at = utcnow()
        await self.session.commit()
        return key

    async def _get(self, organization_id: str, key_id: str) -> ApiKey:
        key = await self.session.scalar(
            select(ApiKey).where(ApiKey.id == key_id, ApiKey.organization_id == organization_id)
        )
        if key is None:
            raise NotFound("API key not found")
        return key


class IngestionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def ingest_one(self, organization_id: str, payload: EventIn, api_key: ApiKey | None = None) -> Event:
        event = Event(
            organization_id=organization_id,
            api_key_id=api_key.id if api_key else None,
            event_type=payload.event_type,
            user_external_id=payload.user_external_id,
            occurred_at=payload.occurred_at or utcnow(),
            received_at=utcnow(),
            properties=payload.properties,
            raw=payload.model_dump(mode="json"),
            idempotency_key=payload.idempotency_key,
        )
        if payload.source:
            event.source_id = await self._source_id(organization_id, payload.source)
        self.session.add(event)
        await self.session.commit()
        return event

    async def ingest_batch(
        self, organization_id: str, payload: BatchEventsIn, api_key: ApiKey | None = None
    ) -> list[Event]:
        events: list[Event] = []
        for item in payload.events:
            event = Event(
                organization_id=organization_id,
                api_key_id=api_key.id if api_key else None,
                event_type=item.event_type,
                user_external_id=item.user_external_id,
                occurred_at=item.occurred_at or utcnow(),
                received_at=utcnow(),
                properties=item.properties,
                raw=item.model_dump(mode="json"),
                idempotency_key=item.idempotency_key,
            )
            events.append(event)
            self.session.add(event)
        await self.session.commit()
        return events

    async def ingest_csv(self, organization_id: str, csv_text: str, api_key: ApiKey | None = None) -> list[Event]:
        reader = csv.DictReader(StringIO(csv_text))
        payloads = [
            EventIn(
                event_type=row.pop("event_type"),
                user_external_id=row.pop("user_external_id", None) or None,
                properties={key: value for key, value in row.items() if value},
            )
            for row in reader
            if row.get("event_type")
        ]
        return await self.ingest_batch(organization_id, BatchEventsIn(events=payloads), api_key)

    async def list_recent(self, organization_id: str, limit: int = 100) -> Sequence[Event]:
        return (
            await self.session.execute(
                select(Event)
                .where(Event.organization_id == organization_id)
                .order_by(Event.received_at.desc())
                .limit(limit)
            )
        ).scalars().all()

    async def mark_processed(self, event_ids: Iterable[str]) -> None:
        await self.session.execute(update(Event).where(Event.id.in_(event_ids)).values(processed=True))
        await self.session.commit()

    async def _source_id(self, organization_id: str, name: str) -> str:
        source = await self.session.scalar(
            select(DataSource).where(DataSource.organization_id == organization_id, DataSource.name == name)
        )
        if source is None:
            source = DataSource(organization_id=organization_id, name=name, type="api")
            self.session.add(source)
            await self.session.flush()
        return source.id


class DashboardService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_query(self, organization_id: str, payload: SavedQueryCreate) -> SavedQuery:
        query = SavedQuery(organization_id=organization_id, **payload.model_dump())
        self.session.add(query)
        await self.session.commit()
        return query

    async def list_queries(self, organization_id: str) -> Sequence[SavedQuery]:
        return (
            await self.session.execute(
                select(SavedQuery).where(SavedQuery.organization_id == organization_id).order_by(SavedQuery.name)
            )
        ).scalars().all()

    async def create_dashboard(self, user: User, payload: DashboardCreate) -> Dashboard:
        dashboard = Dashboard(
            organization_id=user.organization_id,
            owner_id=user.id,
            public_token=secrets.token_urlsafe(18) if payload.visibility == "public" else None,
            **payload.model_dump(),
        )
        self.session.add(dashboard)
        await self.session.commit()
        return await self.session.scalar(
            select(Dashboard).options(selectinload(Dashboard.widgets)).where(Dashboard.id == dashboard.id)
        )

    async def list_dashboards(self, organization_id: str) -> Sequence[Dashboard]:
        return (
            await self.session.execute(
                select(Dashboard)
                .options(selectinload(Dashboard.widgets))
                .where(Dashboard.organization_id == organization_id)
                .order_by(Dashboard.updated_at.desc())
            )
        ).scalars().all()

    async def get_dashboard(self, organization_id: str, dashboard_id: str) -> Dashboard:
        dashboard = await self.session.scalar(
            select(Dashboard)
            .options(selectinload(Dashboard.widgets))
            .where(Dashboard.organization_id == organization_id, Dashboard.id == dashboard_id)
        )
        if dashboard is None:
            raise NotFound("Dashboard not found")
        return dashboard

    async def add_widget(self, organization_id: str, dashboard_id: str, payload: WidgetCreate) -> Widget:
        await self.get_dashboard(organization_id, dashboard_id)
        widget = Widget(organization_id=organization_id, dashboard_id=dashboard_id, **payload.model_dump())
        self.session.add(widget)
        await self.session.commit()
        return widget

    async def public_dashboard(self, token: str) -> Dashboard:
        dashboard = await self.session.scalar(
            select(Dashboard)
            .options(selectinload(Dashboard.widgets))
            .where(Dashboard.public_token == token, Dashboard.visibility == "public")
        )
        if dashboard is None:
            raise NotFound("Dashboard not found")
        return dashboard

    async def run_query(self, organization_id: str, query_id: str | None = None, hours: int = 24) -> dict:
        base_filter = [Event.organization_id == organization_id]
        if query_id:
            query = await self.session.scalar(
                select(SavedQuery).where(SavedQuery.id == query_id, SavedQuery.organization_id == organization_id)
            )
            if query is None:
                raise NotFound("Saved query not found")
            if query.event_type:
                base_filter.append(Event.event_type == query.event_type)

        window_start = utcnow() - timedelta(hours=hours)
        base_filter.append(Event.occurred_at >= window_start)

        count_result = await self.session.scalar(select(func.count(Event.id)).where(*base_filter))

        rows = (
            await self.session.execute(
                select(
                    func.date_trunc("hour", Event.occurred_at).label("bucket"),
                    func.count(Event.id).label("value"),
                )
                .where(*base_filter)
                .group_by(text("bucket"))
                .order_by(text("bucket"))
            )
        ).all()

        return {
            "query_id": query_id,
            "total": float(count_result or 0),
            "series": [{"bucket": row.bucket, "value": float(row.value)} for row in rows],
        }

    async def get_metrics(self, organization_id: str) -> dict:
        now = utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)

        events_today = await self.session.scalar(
            select(func.count(Event.id)).where(
                Event.organization_id == organization_id,
                Event.occurred_at >= today_start,
            )
        )
        events_yesterday = await self.session.scalar(
            select(func.count(Event.id)).where(
                Event.organization_id == organization_id,
                Event.occurred_at >= yesterday_start,
                Event.occurred_at < today_start,
            )
        )
        active_users = await self.session.scalar(
            select(func.count(func.distinct(Event.user_external_id))).where(
                Event.organization_id == organization_id,
                Event.user_external_id.isnot(None),
                Event.occurred_at >= today_start,
            )
        )
        users_yesterday = await self.session.scalar(
            select(func.count(func.distinct(Event.user_external_id))).where(
                Event.organization_id == organization_id,
                Event.user_external_id.isnot(None),
                Event.occurred_at >= yesterday_start,
                Event.occurred_at < today_start,
            )
        )
        error_events_today = await self.session.scalar(
            select(func.count(Event.id)).where(
                Event.organization_id == organization_id,
                Event.event_type.ilike("%error%"),
                Event.occurred_at >= today_start,
            )
        )
        events_t = int(events_today or 0)
        events_y = int(events_yesterday or 0)
        users_t = int(active_users or 0)
        users_y = int(users_yesterday or 0)
        errors_t = int(error_events_today or 0)
        error_rate = round((errors_t / events_t * 100), 1) if events_t else 0.0
        ev_change = round(((events_t - events_y) / events_y * 100), 1) if events_y else 0.0
        u_change = round(((users_t - users_y) / users_y * 100), 1) if users_y else 0.0
        return {
            "events_today": events_t,
            "events_change_pct": ev_change,
            "active_users": users_t,
            "users_change_pct": u_change,
            "error_rate_pct": error_rate,
            "errors_today": errors_t,
        }

    async def get_source_breakdown(self, organization_id: str) -> list[dict]:
        rows = (
            await self.session.execute(
                select(
                    func.coalesce(Event.source_id, "direct").label("source"),
                    func.count(Event.id).label("value"),
                )
                .where(
                    Event.organization_id == organization_id,
                    Event.occurred_at >= utcnow() - timedelta(hours=24),
                )
                .group_by(text("source"))
                .order_by(text("value DESC"))
                .limit(10)
            )
        ).all()
        total = sum(r.value for r in rows) or 1
        return [{"name": r.source, "value": round(r.value / total * 100, 1)} for r in rows]

    async def create_from_template(self, user: User, template_key: str) -> Dashboard:
        templates: dict[str, dict] = {
            "web_analytics": {
                "name": "Web Analytics",
                "description": "Page views, sessions, and conversion funnel",
                "widgets": [
                    {"title": "Page views (24h)", "type": "line", "time_range": "24h"},
                    {"title": "Top event types", "type": "bar", "time_range": "24h"},
                    {"title": "Source mix", "type": "pie", "time_range": "24h"},
                    {"title": "Total events", "type": "kpi", "time_range": "24h"},
                ],
            },
            "sales": {
                "name": "Sales Dashboard",
                "description": "Revenue events, conversion funnel, and user signups",
                "widgets": [
                    {"title": "Checkout events", "type": "line", "time_range": "7d"},
                    {"title": "Revenue funnel", "type": "bar", "time_range": "7d"},
                    {"title": "New signups", "type": "kpi", "time_range": "24h"},
                    {"title": "Error events", "type": "kpi", "time_range": "24h"},
                ],
            },
            "devops": {
                "name": "DevOps Monitoring",
                "description": "API errors, latency events, and system health",
                "widgets": [
                    {"title": "Error rate", "type": "line", "time_range": "1h"},
                    {"title": "Event volume", "type": "bar", "time_range": "1h"},
                    {"title": "API errors", "type": "kpi", "time_range": "1h"},
                    {"title": "Active sources", "type": "table", "time_range": "24h"},
                ],
            },
        }
        tmpl = templates.get(template_key)
        if tmpl is None:
            raise NotFound(f"Template '{template_key}' not found")

        payload = DashboardCreate(name=tmpl["name"], description=tmpl["description"])
        dashboard = await self.create_dashboard(user, payload)

        for i, w in enumerate(tmpl["widgets"]):
            widget = Widget(
                organization_id=user.organization_id,
                dashboard_id=dashboard.id,
                title=w["title"],
                type=w["type"],
                time_range=w["time_range"],
                layout={"x": (i % 2) * 6, "y": (i // 2) * 3, "w": 6, "h": 3},
            )
            self.session.add(widget)
        await self.session.commit()
        return await self.get_dashboard(user.organization_id, dashboard.id)


class AlertService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, organization_id: str, payload: AlertRuleCreate) -> AlertRule:
        rule = AlertRule(organization_id=organization_id, **payload.model_dump())
        self.session.add(rule)
        await self.session.commit()
        return rule

    async def list(self, organization_id: str) -> Sequence[AlertRule]:
        return (
            await self.session.execute(
                select(AlertRule).where(AlertRule.organization_id == organization_id).order_by(AlertRule.name)
            )
        ).scalars().all()

    async def history(self, organization_id: str, rule_id: str) -> Sequence[AlertEvent]:
        return (
            await self.session.execute(
                select(AlertEvent)
                .where(AlertEvent.organization_id == organization_id, AlertEvent.alert_rule_id == rule_id)
                .order_by(AlertEvent.created_at.desc())
            )
        ).scalars().all()

    async def mute(self, organization_id: str, rule_id: str, minutes: int) -> AlertRule:
        rule = await self._get(organization_id, rule_id)
        rule.status = "muted"
        rule.muted_until = utcnow() + timedelta(minutes=minutes)
        await self.session.commit()
        return rule

    async def evaluate(self, organization_id: str, rule_id: str) -> AlertEvent:
        rule = await self._get(organization_id, rule_id)
        window_start = utcnow() - timedelta(seconds=rule.window_seconds)

        base_filters = [
            Event.organization_id == organization_id,
            Event.occurred_at >= window_start,
        ]
        if rule.event_type:
            base_filters.append(Event.event_type == rule.event_type)

        metric = getattr(rule, "metric", "event_count") or "event_count"
        if metric == "unique_users":
            value = await self.session.scalar(
                select(func.count(func.distinct(Event.user_external_id))).where(*base_filters)
            )
        elif metric == "error_rate":
            total = await self.session.scalar(select(func.count(Event.id)).where(*base_filters)) or 0
            error_filters = base_filters + [Event.event_type.ilike("%error%")]
            errors = await self.session.scalar(select(func.count(Event.id)).where(*error_filters)) or 0
            value = round((errors / total * 100) if total > 0 else 0.0, 2)
        else:
            value = await self.session.scalar(select(func.count(Event.id)).where(*base_filters))

        numeric = float(value or 0)
        triggered = self._compare(numeric, rule.operator, rule.threshold)
        rule.status = "triggered" if triggered else "resolved"
        rule.last_evaluated_at = utcnow()
        event = AlertEvent(
            organization_id=organization_id,
            alert_rule_id=rule.id,
            status=rule.status,
            value=numeric,
            message=f"{rule.name}: value {numeric} {rule.operator} {rule.threshold}",
        )
        self.session.add(event)
        if triggered:
            if "in_app" in rule.channels:
                self.session.add(
                    Notification(
                        organization_id=organization_id,
                        channel="in_app",
                        title=f"Alert triggered: {rule.name}",
                        body=event.message,
                        payload={"alert_rule_id": rule.id, "value": numeric},
                    )
                )
            if "email" in rule.channels and rule.email_recipients:
                from app.core.email import send_alert_email

                org = await self.session.get(Organization, organization_id)
                await send_alert_email(
                    to=rule.email_recipients,
                    rule_name=rule.name,
                    status=rule.status,
                    value=numeric,
                    message=event.message,
                    org_name=org.name if org else organization_id,
                )
            if "webhook" in rule.channels and rule.webhook_url:
                await self._dispatch_webhook(
                    rule.webhook_url,
                    {
                        "type": "alert.triggered",
                        "rule": rule.name,
                        "value": numeric,
                        "message": event.message,
                        "organization_id": organization_id,
                    },
                )
        await self.session.commit()
        return event

    @staticmethod
    async def _dispatch_webhook(url: str, payload: dict) -> None:
        try:
            async with httpx.AsyncClient(timeout=settings.webhook_timeout_seconds) as client:
                await client.post(url, json=payload)
        except Exception:
            pass

    async def _get(self, organization_id: str, rule_id: str) -> AlertRule:
        rule = await self.session.scalar(
            select(AlertRule).where(AlertRule.id == rule_id, AlertRule.organization_id == organization_id)
        )
        if rule is None:
            raise NotFound("Alert rule not found")
        return rule

    @staticmethod
    def _compare(value: float, operator: str, threshold: float) -> bool:
        return {
            ">": value > threshold,
            ">=": value >= threshold,
            "<": value < threshold,
            "<=": value <= threshold,
            "==": value == threshold,
        }[operator]


class ReportService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, organization_id: str, payload: ReportScheduleCreate) -> ReportSchedule:
        schedule = ReportSchedule(organization_id=organization_id, **payload.model_dump(mode="json"))
        self.session.add(schedule)
        await self.session.commit()
        return schedule

    async def list(self, organization_id: str) -> Sequence[ReportSchedule]:
        return (
            await self.session.execute(
                select(ReportSchedule)
                .where(ReportSchedule.organization_id == organization_id)
                .order_by(ReportSchedule.name)
            )
        ).scalars().all()

    async def run_now(self, organization_id: str, schedule_id: str) -> ReportRun:
        schedule = await self.session.scalar(
            select(ReportSchedule).where(
                ReportSchedule.id == schedule_id,
                ReportSchedule.organization_id == organization_id,
            )
        )
        if schedule is None:
            raise NotFound("Report schedule not found")

        started = utcnow()
        run = ReportRun(
            organization_id=organization_id,
            schedule_id=schedule.id,
            status="running",
            started_at=started,
        )
        self.session.add(run)
        await self.session.flush()

        try:
            rows = await self._build_report_rows(organization_id)
            artifact_url = await self._generate_artifact(schedule, rows)
            run.status = "completed"
            run.artifact_url = artifact_url
            run.completed_at = utcnow()
            schedule.last_run_at = utcnow()

            if schedule.recipients:
                org = await self.session.get(Organization, organization_id)
                from app.core.email import send_report_email

                await send_report_email(
                    to=schedule.recipients,
                    report_name=schedule.name,
                    rows=rows,
                    org_name=org.name if org else organization_id,
                )
        except Exception as exc:
            run.status = "failed"
            run.error = str(exc)
            run.completed_at = utcnow()

        await self.session.commit()
        return run

    async def _build_report_rows(self, organization_id: str) -> list[dict]:
        total_events = await self.session.scalar(
            select(func.count(Event.id)).where(Event.organization_id == organization_id)
        )
        unique_users = await self.session.scalar(
            select(func.count(func.distinct(Event.user_external_id))).where(
                Event.organization_id == organization_id,
                Event.user_external_id.isnot(None),
            )
        )
        last_24h = await self.session.scalar(
            select(func.count(Event.id)).where(
                Event.organization_id == organization_id,
                Event.occurred_at >= utcnow() - timedelta(hours=24),
            )
        )
        return [
            {"label": "Total events", "value": total_events or 0},
            {"label": "Unique users", "value": unique_users or 0},
            {"label": "Events (last 24h)", "value": last_24h or 0},
        ]

    @staticmethod
    async def _generate_artifact(schedule: ReportSchedule, rows: list[dict]) -> str:
        from app.core.config import settings as _settings

        artifacts_dir = _settings.report_artifacts_dir
        os.makedirs(artifacts_dir, exist_ok=True)

        ext = "csv" if schedule.format == "png" else "pdf"
        filename = f"{schedule.id}_{utcnow().date()}.{ext}"
        filepath = os.path.join(artifacts_dir, filename)

        if ext == "pdf":
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(0, 12, schedule.name, ln=True)
            pdf.set_font("Helvetica", size=11)
            pdf.cell(0, 8, f"Generated: {utcnow().strftime('%Y-%m-%d %H:%M UTC')}", ln=True)
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(100, 8, "Metric", border=1)
            pdf.cell(60, 8, "Value", border=1, ln=True)
            pdf.set_font("Helvetica", size=11)
            for row in rows:
                pdf.cell(100, 8, str(row["label"]), border=1)
                pdf.cell(60, 8, str(row["value"]), border=1, ln=True)
            pdf.output(filepath)
        else:
            with open(filepath, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Metric", "Value"])
                for row in rows:
                    writer.writerow([row["label"], row["value"]])

        return f"{_settings.public_base_url}/artifacts/{filename}"

    async def history(self, organization_id: str, schedule_id: str) -> Sequence[ReportRun]:
        return (
            await self.session.execute(
                select(ReportRun)
                .where(ReportRun.organization_id == organization_id, ReportRun.schedule_id == schedule_id)
                .order_by(ReportRun.created_at.desc())
            )
        ).scalars().all()


class AdminService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def update_feature_flags(self, organization_id: str, flags: dict[str, bool]) -> dict[str, bool]:
        organization = await self._organization(organization_id)
        organization.feature_flags = flags
        await self.session.commit()
        return organization.feature_flags

    async def update_retention(self, organization_id: str, retention_days: int) -> int:
        organization = await self._organization(organization_id)
        organization.retention_days = retention_days
        await self.session.commit()
        return retention_days

    async def run_sql_sandbox(self, organization_id: str, payload: SqlSandboxRequest) -> dict:
        sql = payload.sql.strip()
        lowered = sql.lower()
        if not lowered.startswith("select") or ";" in sql:
            raise AuthenticationFailed("Only single SELECT statements are allowed", status_code=400)
        if ":organization_id" not in sql:
            raise AuthenticationFailed("Sandbox queries must bind :organization_id", status_code=400)
        scoped_sql = f"select * from ({sql}) sandbox_query limit :limit"
        explain_sql = f"explain {sql}"
        params = {"limit": payload.limit, "organization_id": organization_id}
        rows = (await self.session.execute(text(scoped_sql), params)).mappings().all()
        plan_rows = (await self.session.execute(text(explain_sql), params)).all()
        return {
            "columns": list(rows[0].keys()) if rows else [],
            "rows": [dict(row) for row in rows],
            "plan": [str(row[0]) for row in plan_rows],
        }

    async def create_webhook_delivery(
        self, organization_id: str, payload: WebhookDeliveryCreate
    ) -> WebhookDelivery:
        delivery = WebhookDelivery(organization_id=organization_id, **payload.model_dump())
        self.session.add(delivery)
        await self.session.commit()
        return delivery

    async def list_webhook_deliveries(self, organization_id: str) -> Sequence[WebhookDelivery]:
        return (
            await self.session.execute(
                select(WebhookDelivery)
                .where(WebhookDelivery.organization_id == organization_id)
                .order_by(WebhookDelivery.created_at.desc())
            )
        ).scalars().all()

    async def retry_webhook_delivery(self, organization_id: str, delivery_id: str) -> WebhookDelivery:
        delivery = await self.session.scalar(
            select(WebhookDelivery).where(
                WebhookDelivery.id == delivery_id,
                WebhookDelivery.organization_id == organization_id,
            )
        )
        if delivery is None:
            raise NotFound("Webhook delivery not found")
        delivery.status = "pending"
        delivery.next_attempt_at = utcnow()
        await self.session.commit()
        return delivery

    async def _organization(self, organization_id: str) -> Organization:
        organization = await self.session.get(Organization, organization_id)
        if organization is None:
            raise NotFound("Organization not found")
        return organization
