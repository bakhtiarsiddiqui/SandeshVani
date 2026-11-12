import uuid

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.db.sync import create_sync_session_factory
from app.workers.audience_import_worker import AudienceImportWorker


@celery_app.task(
    bind=True,
    name="app.workers.audience_import_tasks.process_audience_import",
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=5,
)
def process_audience_import(
    self,
    job_id: str,
    organization_id: str,
) -> dict:
    settings = get_settings()
    engine, session_factory = create_sync_session_factory(
        settings.get_database_url()
    )
    worker = AudienceImportWorker(
        session_factory,
        settings.audience_import_storage_dir,
        lease_seconds=settings.audience_import_worker_lease_seconds,
    )
    try:
        return worker.process(
            uuid.UUID(job_id),
            uuid.UUID(organization_id),
        )
    except Exception as error:
        if self.request.retries >= self.max_retries:
            worker.mark_retry_exhausted(
                uuid.UUID(job_id),
                uuid.UUID(organization_id),
            )
            raise
        raise self.retry(
            exc=error,
            countdown=min(30 * (2**self.request.retries), 300),
        ) from error
    finally:
        engine.dispose()
