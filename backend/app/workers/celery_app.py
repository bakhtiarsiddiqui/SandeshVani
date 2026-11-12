from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "sandeshvani",
    broker=settings.redis_url,
    include=["app.workers.audience_imports"],
)
celery_app.conf.update(
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_ignore_result=True,
    task_routes={
        "app.workers.audience_imports.process_audience_import": {
            "queue": "audience-imports"
        },
        "app.workers.audience_imports.publish_pending_audience_imports": {
            "queue": "default"
        },
    },
    beat_schedule={
        "publish-pending-audience-imports": {
            "task": "app.workers.audience_imports.publish_pending_audience_imports",
            "schedule": 10.0,
            "options": {"queue": "default"},
        }
    },
)
