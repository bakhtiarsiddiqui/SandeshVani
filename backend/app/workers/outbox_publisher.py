import uuid

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.db.sync import create_sync_session_factory
from app.services.outbox_service import publish_pending_outbox_events
from app.workers.audience_import_tasks import process_audience_import


@celery_app.task(name="app.workers.outbox_publisher.publish_pending_outbox")
def publish_pending_outbox() -> int:
    settings = get_settings()
    engine, session_factory = create_sync_session_factory(
        settings.get_database_url()
    )

    def publish(job_id: uuid.UUID, organization_id: uuid.UUID, event_id: uuid.UUID):
        process_audience_import.apply_async(
            args=[str(job_id), str(organization_id)],
            task_id=str(event_id),
        )

    try:
        return publish_pending_outbox_events(
            session_factory,
            publish,
            batch_size=50,
            lease_seconds=60,
        )
    finally:
        engine.dispose()
