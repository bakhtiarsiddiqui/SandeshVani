import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from app.models.audience_import_job import AudienceImportJob
from app.models.governance import CampaignExecution
from app.models.organization import Organization
from app.models.outbox_event import OutboxEvent

logger = logging.getLogger(__name__)


def _set_tenant_context(session: Session, organization_id: uuid.UUID) -> None:
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        session.execute(
            text("SELECT set_config('app.current_org', :org_id, true)"),
            {"org_id": str(organization_id)},
        )


def publish_pending_outbox_events(
    session_factory: Callable[[], Session],
    publish_import_task: Callable[[uuid.UUID, uuid.UUID, uuid.UUID], None],
    *,
    batch_size: int = 50,
    lease_seconds: int = 60,
    max_attempts: int = 12,
    publish_execution_task: Callable[[uuid.UUID, uuid.UUID, uuid.UUID], None] | None = None,
) -> int:
    """Publish durable outbox records, claiming them tenant by tenant."""
    with session_factory() as session:
        organization_ids = list(
            session.scalars(
                select(Organization.id).where(Organization.status == "active")
            ).all()
        )

    published_count = 0
    for organization_id in organization_ids:
        now = datetime.now(UTC)
        with session_factory.begin() as session:
            _set_tenant_context(session, organization_id)
            events = list(
                session.scalars(
                    select(OutboxEvent)
                    .where(
                        OutboxEvent.organization_id == organization_id,
                        OutboxEvent.status.in_(("pending", "publishing")),
                        OutboxEvent.available_at <= now,
                        or_(
                            OutboxEvent.locked_until.is_(None),
                            OutboxEvent.locked_until <= now,
                        ),
                    )
                    .order_by(OutboxEvent.available_at, OutboxEvent.created_at)
                    .limit(batch_size)
                    .with_for_update(skip_locked=True)
                ).all()
            )
            claimed = []
            for event in events:
                event.status = "publishing"
                event.attempt_count += 1
                event.locked_until = now + timedelta(seconds=lease_seconds)
                claimed.append(
                    (
                        event.id,
                        event.aggregate_id,
                        event.attempt_count,
                        event.event_type,
                    )
                )

        for event_id, aggregate_id, attempt_count, event_type in claimed:
            try:
                if event_type == "audience_import.queued":
                    publish_import_task(aggregate_id, organization_id, event_id)
                elif event_type == "campaign.mock_execute.queued":
                    if publish_execution_task is None:
                        raise RuntimeError("Mock execution task publisher is not configured")
                    publish_execution_task(aggregate_id, organization_id, event_id)
                else:
                    raise RuntimeError(f"Unsupported outbox event type: {event_type}")
            except Exception:
                logger.exception(
                    "Outbox publication failed",
                    extra={"outbox_event_id": str(event_id)},
                )
                retry_at = datetime.now(UTC) + timedelta(
                    seconds=min(5 * (2 ** min(attempt_count, 7)), 600)
                )
                with session_factory.begin() as session:
                    _set_tenant_context(session, organization_id)
                    event = session.scalar(
                        select(OutboxEvent)
                        .where(
                            OutboxEvent.organization_id == organization_id,
                            OutboxEvent.id == event_id,
                        )
                        .with_for_update()
                    )
                    if event is None:
                        continue
                    event.locked_until = None
                    event.last_error_code = "BROKER_PUBLISH_FAILED"
                    if attempt_count >= max_attempts:
                        event.status = "dead_letter"
                        if event_type == "audience_import.queued":
                            job = session.scalar(
                                select(AudienceImportJob)
                                .where(
                                    AudienceImportJob.organization_id == organization_id,
                                    AudienceImportJob.id == aggregate_id,
                                )
                                .with_for_update()
                            )
                            if job is not None and job.status not in {
                                "completed", "completed_with_errors", "failed",
                            }:
                                job.status = "failed"
                                job.last_error_code = "QUEUE_DELIVERY_FAILED"
                                job.completed_at = datetime.now(UTC)
                                job.worker_token = None
                                job.lease_expires_at = None
                        elif event_type == "campaign.mock_execute.queued":
                            execution = session.scalar(
                                select(CampaignExecution)
                                .where(
                                    CampaignExecution.organization_id == organization_id,
                                    CampaignExecution.id == aggregate_id,
                                )
                                .with_for_update()
                            )
                            if execution is not None and execution.status != "completed":
                                execution.status = "failed"
                    else:
                        event.status = "pending"
                        event.available_at = retry_at
                continue

            with session_factory.begin() as session:
                _set_tenant_context(session, organization_id)
                event = session.scalar(
                    select(OutboxEvent)
                    .where(
                        OutboxEvent.organization_id == organization_id,
                        OutboxEvent.id == event_id,
                    )
                    .with_for_update()
                )
                if event is not None:
                    event.status = "published"
                    event.published_at = datetime.now(UTC)
                    event.locked_until = None
                    event.last_error_code = None
                    published_count += 1

    return published_count
