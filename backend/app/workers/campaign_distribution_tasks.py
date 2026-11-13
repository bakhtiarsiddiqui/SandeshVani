import uuid

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.db.sync import create_sync_session_factory
from app.workers.mock_campaign_worker import MockCampaignWorker


@celery_app.task(
    bind=True,
    name="app.workers.campaign_distribution_tasks.execute_mock_campaign",
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=5,
)
def execute_mock_campaign(self, execution_id: str, organization_id: str) -> dict:
    settings = get_settings()
    engine, session_factory = create_sync_session_factory(settings.get_database_url())
    worker = MockCampaignWorker(session_factory, batch_size=500)
    try:
        return worker.process(uuid.UUID(execution_id), uuid.UUID(organization_id))
    except Exception as error:
        if self.request.retries >= self.max_retries:
            worker.mark_failed(
                uuid.UUID(execution_id),
                uuid.UUID(organization_id),
                "WORKER_RETRIES_EXHAUSTED",
            )
            raise
        raise self.retry(
            exc=error,
            countdown=min(30 * (2**self.request.retries), 300),
        ) from error
    finally:
        engine.dispose()
