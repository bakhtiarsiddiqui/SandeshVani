from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "sandeshvani",
    broker=settings.redis_url,
    include=[
        "app.workers.audience_import_tasks",
        "app.workers.campaign_distribution_tasks",
        "app.workers.outbox_publisher",
    ],
)
celery_app.conf.update(
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    broker_transport_options={"visibility_timeout": 3600},
    beat_schedule={
        "publish-pending-outbox-events": {
            "task": "app.workers.outbox_publisher.publish_pending_outbox",
            "schedule": 10.0,
        }
    },
)
