import os
import threading
import uuid

import pytest
from celery.contrib.testing.worker import start_worker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.celery_app import celery_app
from app.models.audience_import_job import AudienceImportJob
from app.models.audience_import_upload import AudienceImportUpload
from app.models.base import Base
from app.models.governance import CampaignExecution
from app.models.organization import Organization
from app.models.outbox_event import OutboxEvent
from app.models.user import User
from app.workers.outbox_service import publish_pending_outbox_events


@pytest.fixture
def outbox_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield engine, factory
    engine.dispose()


def _seed_pending_event(factory):
    organization_id = uuid.uuid4()
    user_id = uuid.uuid4()
    upload_id = uuid.uuid4()
    job_id = uuid.uuid4()
    event_id = uuid.uuid4()
    with factory.begin() as session:
        session.add(
            Organization(
                id=organization_id,
                name="Outbox Test",
                slug=f"outbox-{organization_id.hex[:10]}",
                status="active",
            )
        )
        session.add(
            User(
                id=user_id,
                email=f"{user_id.hex}@example.org",
                normalized_email=f"{user_id.hex}@example.org",
                password_hash="test-hash",
                full_name="Outbox Actor",
                status="active",
            )
        )
        session.flush()
        session.add(
            AudienceImportUpload(
                id=upload_id,
                organization_id=organization_id,
                uploaded_by_id=user_id,
                byte_size=32,
                row_count=1,
                sha256="a" * 64,
            )
        )
        session.add(
            AudienceImportJob(
                id=job_id,
                organization_id=organization_id,
                upload_id=upload_id,
                uploaded_by_id=user_id,
                status="queued",
                total_rows=1,
                processed_rows=0,
                imported_rows=0,
                error_rows=0,
                chunk_size=1,
            )
        )
        session.add(
            OutboxEvent(
                id=event_id,
                organization_id=organization_id,
                aggregate_type="audience_import_job",
                aggregate_id=job_id,
                event_type="audience_import.queued",
                payload={"job_id": str(job_id)},
                status="pending",
                attempt_count=0,
            )
        )
    return organization_id, job_id, event_id


def test_outbox_publishes_once_and_marks_event_published(outbox_db):
    _, factory = outbox_db
    organization_id, job_id, event_id = _seed_pending_event(factory)
    published = []

    def publisher(received_job_id, received_org_id, received_event_id):
        published.append((received_job_id, received_org_id, received_event_id))

    first = publish_pending_outbox_events(factory, publisher)
    second = publish_pending_outbox_events(factory, publisher)

    assert first == 1
    assert second == 0
    assert published == [(job_id, organization_id, event_id)]
    with factory() as session:
        event = session.get(OutboxEvent, event_id)
    assert event.status == "published"
    assert event.attempt_count == 1
    assert event.published_at is not None


def test_outbox_dead_letters_after_bounded_publish_failures(outbox_db):
    _, factory = outbox_db
    _, job_id, event_id = _seed_pending_event(factory)

    def failing_publisher(*_):
        raise RuntimeError("simulated broker outage")

    published = publish_pending_outbox_events(
        factory,
        failing_publisher,
        max_attempts=1,
    )

    assert published == 0
    with factory() as session:
        event = session.get(OutboxEvent, event_id)
        job = session.get(AudienceImportJob, job_id)
    assert event.status == "dead_letter"
    assert event.last_error_code == "BROKER_PUBLISH_FAILED"
    assert job.status == "failed"
    assert job.last_error_code == "QUEUE_DELIVERY_FAILED"


_REDIS_TASK_NAME = "tests.capture_audience_import_identifiers"
_REDIS_TASK_RECEIVED = threading.Event()
_REDIS_TASK_PAYLOAD: dict[str, str] = {}


@celery_app.task(name=_REDIS_TASK_NAME)
def _capture_audience_import_identifiers(
    job_id: str, organization_id: str, event_id: str
) -> None:
    _REDIS_TASK_PAYLOAD.update(
        job_id=job_id,
        organization_id=organization_id,
        event_id=event_id,
    )
    _REDIS_TASK_RECEIVED.set()


@pytest.mark.skipif(
    not os.getenv("SANDESHVANI_REDIS_TEST_URL"),
    reason="SANDESHVANI_REDIS_TEST_URL is not configured",
)
def test_outbox_dispatches_identifier_payload_through_live_redis_worker(outbox_db):
    _, factory = outbox_db
    organization_id, job_id, event_id = _seed_pending_event(factory)
    broker_url = os.environ["SANDESHVANI_REDIS_TEST_URL"]
    queue_name = f"audience-import-smoke-{uuid.uuid4().hex}"
    _REDIS_TASK_RECEIVED.clear()
    _REDIS_TASK_PAYLOAD.clear()
    celery_app.conf.update(broker_url=broker_url)

    def publish(received_job_id, received_org_id, received_event_id):
        celery_app.send_task(
            _REDIS_TASK_NAME,
            args=[
                str(received_job_id),
                str(received_org_id),
                str(received_event_id),
            ],
            task_id=str(received_event_id),
            queue=queue_name,
        )

    assert "publish-pending-outbox-events" in celery_app.conf.beat_schedule

    with start_worker(
        celery_app,
        pool="solo",
        queues=[queue_name],
        perform_ping_check=False,
        loglevel="ERROR",
    ):
        published = publish_pending_outbox_events(factory, publish)
        assert published == 1
        assert _REDIS_TASK_RECEIVED.wait(timeout=10)

    assert _REDIS_TASK_PAYLOAD == {
        "job_id": str(job_id),
        "organization_id": str(organization_id),
        "event_id": str(event_id),
    }
    with factory() as session:
        event = session.get(OutboxEvent, event_id)
    assert event is not None
    assert event.status == "published"
    assert event.published_at is not None


def test_outbox_dispatches_mock_execution_to_campaign_worker(outbox_db):
    _, factory = outbox_db
    organization_id = uuid.uuid4()
    user_id = uuid.uuid4()
    execution_id = uuid.uuid4()
    event_id = uuid.uuid4()
    with factory.begin() as session:
        session.add(
            Organization(
                id=organization_id,
                name="Campaign Outbox Test",
                slug=f"campaign-outbox-{organization_id.hex[:10]}",
                status="active",
            )
        )
        session.add(
            User(
                id=user_id,
                email=f"{user_id.hex}@example.org",
                normalized_email=f"{user_id.hex}@example.org",
                password_hash="test-hash",
                full_name="Campaign Actor",
                status="active",
            )
        )
        session.flush()
        session.add(
            CampaignExecution(
                id=execution_id,
                organization_id=organization_id,
                campaign_version_id=uuid.uuid4(),
                execution_mode="mock",
                status="queued",
                initiated_by=user_id,
            )
        )
        session.add(
            OutboxEvent(
                id=event_id,
                organization_id=organization_id,
                aggregate_type="campaign_execution",
                aggregate_id=execution_id,
                event_type="campaign.mock_execute.queued",
                payload={"execution_id": str(execution_id)},
                status="pending",
                attempt_count=0,
            )
        )

    published = []

    def publish_execution(received_execution, received_org, received_event):
        published.append((received_execution, received_org, received_event))

    result = publish_pending_outbox_events(
        factory,
        lambda *_args: None,
        publish_execution_task=publish_execution,
    )

    assert result == 1
    assert published == [(execution_id, organization_id, event_id)]
    with factory() as session:
        event = session.get(OutboxEvent, event_id)
    assert event is not None and event.status == "published"
