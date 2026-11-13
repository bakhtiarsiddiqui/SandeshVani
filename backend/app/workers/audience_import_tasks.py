import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.db.sync import create_sync_session_factory
from app.models.audience_import_job import AudienceImportJob
from app.models.audience_import_upload import AudienceImportUpload
from app.models.organization import Organization
from app.workers.audience_import_worker import AudienceImportWorker

logger = logging.getLogger(__name__)


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
    engine, session_factory = create_sync_session_factory(settings.get_database_url())
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


def _set_tenant_context(session: Session, organization_id: uuid.UUID) -> None:
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        session.execute(
            text("SELECT set_config('app.current_org', :org_id, true)"),
            {"org_id": str(organization_id)},
        )


def cleanup_expired_audience_files(
    session_factory,
    storage_dir,
    *,
    now: datetime | None = None,
    batch_size: int = 100,
) -> int:
    """Delete expired CSV payloads only after their import jobs are terminal.

    Upload and job metadata are retained. Each file deletion is idempotent:
    if the process stops after unlink but before COMMIT, the next sweep retries
    the missing file and marks its metadata as deleted.
    """
    current = now or datetime.now(UTC)
    root = storage_dir.expanduser()
    if root.is_symlink():
        raise RuntimeError("Audience import storage directory must not be a symlink")
    if not root.exists():
        return 0
    if not root.is_dir():
        raise RuntimeError("Audience import storage path is not a directory")

    with session_factory() as session:
        organization_ids = list(
            session.scalars(select(Organization.id).order_by(Organization.id)).all()
        )

    deleted_count = 0
    terminal = ("completed", "completed_with_errors", "failed")
    for organization_id in organization_ids:
        with session_factory.begin() as session:
            _set_tenant_context(session, organization_id)
            uploads = list(
                session.scalars(
                    select(AudienceImportUpload)
                    .join(
                        AudienceImportJob,
                        (
                            AudienceImportJob.organization_id
                            == AudienceImportUpload.organization_id
                        )
                        & (AudienceImportJob.upload_id == AudienceImportUpload.id),
                    )
                    .where(
                        AudienceImportUpload.organization_id == organization_id,
                        AudienceImportUpload.retention_expires_at <= current,
                        AudienceImportUpload.file_deleted_at.is_(None),
                        AudienceImportJob.status.in_(terminal),
                    )
                    .order_by(AudienceImportUpload.retention_expires_at)
                    .limit(batch_size)
                    .with_for_update(skip_locked=True, of=AudienceImportUpload)
                ).all()
            )
            for upload in uploads:
                path = root / f"{upload.id.hex}.csv"
                try:
                    # unlink removes a symlink itself; it never follows its
                    # target. Generated UUID names cannot escape the root.
                    path.unlink(missing_ok=True)
                except OSError:
                    logger.exception(
                        "Could not delete expired audience import file",
                        extra={
                            "audience_import_upload_id": str(upload.id),
                            "organization_id": str(organization_id),
                        },
                    )
                    continue
                upload.file_deleted_at = current
                deleted_count += 1

    return deleted_count


@celery_app.task(
    name="app.workers.audience_import_tasks.cleanup_expired_audience_files"
)
def cleanup_expired_audience_files_task() -> int:
    """Daily Celery task for retention-based private upload deletion."""
    settings = get_settings()
    engine, session_factory = create_sync_session_factory(settings.get_database_url())
    try:
        return cleanup_expired_audience_files(
            session_factory,
            settings.audience_import_storage_dir,
            batch_size=100,
        )
    finally:
        engine.dispose()
