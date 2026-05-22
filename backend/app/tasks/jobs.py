import asyncio
import logging
from datetime import timedelta

import httpx
from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.core.security import utcnow
from app.models import AlertRule, Event, Organization, ReportSchedule, WebhookDelivery
from app.services import AlertService, IngestionService, ReportService
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.jobs.process_events",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def process_events(self, event_ids: list[str]) -> dict[str, int]:
    async def run() -> dict[str, int]:
        async with SessionLocal() as session:
            await IngestionService(session).mark_processed(event_ids)
            return {"processed": len(event_ids)}

    return asyncio.run(run())


@celery_app.task(
    name="app.tasks.jobs.evaluate_due_alerts",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def evaluate_due_alerts(self) -> dict[str, int]:
    async def run() -> dict[str, int]:
        async with SessionLocal() as session:
            rules = (
                await session.execute(
                    select(AlertRule).where(
                        AlertRule.status != "muted",
                        (AlertRule.muted_until.is_(None)) | (AlertRule.muted_until <= utcnow()),
                    )
                )
            ).scalars().all()
            service = AlertService(session)
            evaluated = 0
            for rule in rules:
                try:
                    await service.evaluate(rule.organization_id, rule.id)
                    evaluated += 1
                except Exception:
                    logger.exception("Failed to evaluate alert rule %s", rule.id)
            return {"evaluated": evaluated}

    try:
        return asyncio.run(run())
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.jobs.run_scheduled_reports",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def run_scheduled_reports(self) -> dict[str, int]:
    async def run() -> dict[str, int]:
        async with SessionLocal() as session:
            schedules = (
                await session.execute(select(ReportSchedule).where(ReportSchedule.is_active.is_(True)))
            ).scalars().all()
            service = ReportService(session)
            queued = 0
            for schedule in schedules:
                try:
                    await service.run_now(schedule.organization_id, schedule.id)
                    queued += 1
                except Exception:
                    logger.exception("Failed to run report schedule %s", schedule.id)
            return {"queued": queued}

    try:
        return asyncio.run(run())
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.jobs.apply_retention",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def apply_retention(self) -> dict[str, int]:
    async def run() -> dict[str, int]:
        async with SessionLocal() as session:
            orgs = (await session.execute(select(Organization))).scalars().all()
            total_deleted = 0
            for org in orgs:
                cutoff = utcnow() - timedelta(days=org.retention_days)
                result = await session.execute(
                    delete(Event).where(
                        Event.organization_id == org.id,
                        Event.occurred_at < cutoff,
                    )
                )
                total_deleted += result.rowcount
            await session.commit()
            return {"deleted": total_deleted}

    try:
        return asyncio.run(run())
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.jobs.dispatch_pending_webhooks",
    bind=True,
    max_retries=5,
    default_retry_delay=30,
    retry_backoff=True,
)
def dispatch_pending_webhooks(self) -> dict[str, int]:
    async def run() -> dict[str, int]:
        async with SessionLocal() as session:
            deliveries = (
                await session.execute(
                    select(WebhookDelivery).where(
                        WebhookDelivery.status == "pending",
                        (WebhookDelivery.next_attempt_at.is_(None))
                        | (WebhookDelivery.next_attempt_at <= utcnow()),
                    ).limit(50)
                )
            ).scalars().all()

            dispatched = 0
            for delivery in deliveries:
                delivery.attempts += 1
                try:
                    async with httpx.AsyncClient(timeout=8.0) as client:
                        resp = await client.post(delivery.target_url, json=delivery.payload)
                        if resp.is_success:
                            delivery.status = "delivered"
                            dispatched += 1
                        else:
                            delivery.status = "failed"
                            delivery.next_attempt_at = utcnow() + timedelta(minutes=5 * delivery.attempts)
                except Exception as exc:
                    logger.warning("Webhook %s attempt %d failed: %s", delivery.id, delivery.attempts, exc)
                    if delivery.attempts >= 5:
                        delivery.status = "dead"
                    else:
                        delivery.status = "pending"
                        delivery.next_attempt_at = utcnow() + timedelta(minutes=5 * delivery.attempts)

            await session.commit()
            return {"dispatched": dispatched, "total": len(deliveries)}

    try:
        return asyncio.run(run())
    except Exception as exc:
        raise self.retry(exc=exc)
