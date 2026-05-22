from celery import Celery

from app.core.config import settings

_broker = settings.celery_broker_url
_backend = settings.celery_result_backend

# Fall back to in-process memory transport when no broker is configured/available.
# Tasks run synchronously inline; no Redis or external broker needed for local dev.
if _broker.startswith("memory://") or _broker == "":
    _backend = "cache+memory://"

celery_app = Celery(
    "wexa",
    broker=_broker,
    backend=_backend,
    include=["app.tasks.jobs"],
)

if _broker.startswith("memory://") or _broker == "":
    celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)

celery_app.conf.beat_schedule = {
    "evaluate-alerts-every-minute": {
        "task": "app.tasks.jobs.evaluate_due_alerts",
        "schedule": 60.0,
    },
    "run-scheduled-reports-every-five-minutes": {
        "task": "app.tasks.jobs.run_scheduled_reports",
        "schedule": 300.0,
    },
    "dispatch-pending-webhooks-every-30s": {
        "task": "app.tasks.jobs.dispatch_pending_webhooks",
        "schedule": 30.0,
    },
    "apply-retention-daily": {
        "task": "app.tasks.jobs.apply_retention",
        "schedule": 86400.0,
    },
}

celery_app.conf.task_acks_late = True
celery_app.conf.task_reject_on_worker_lost = True
celery_app.conf.worker_prefetch_multiplier = 1

