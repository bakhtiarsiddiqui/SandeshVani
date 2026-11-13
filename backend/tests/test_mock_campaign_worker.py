from datetime import UTC, datetime
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.audience_member import AudienceMember
from app.models.base import Base
from app.models.governance import (
    AudienceSegment,
    AudienceSegmentVersion,
    Campaign,
    CampaignApproval,
    CampaignExecution,
    CampaignVersion,
    ChannelConsentEvent,
    ChannelDelivery,
    DeliveryAttempt,
    ProcessingBasisEvent,
    SuppressionEvent,
)
from app.models.organization import Organization
from app.models.user import User
from app.services.governance_service import content_sha256
from app.workers.mock_campaign_worker import MockCampaignWorker


def test_mock_worker_rechecks_basis_consent_and_suppression_per_channel(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'mock-worker.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    now = datetime.now(UTC)

    with factory.begin() as session:
        org = Organization(name="Mock Worker Org", slug="mock-worker-org")
        user = User(
            email="mock-worker@example.test",
            normalized_email="mock-worker@example.test",
            password_hash="not-used",
            full_name="Mock Worker",
            status="active",
        )
        session.add_all([org, user])
        session.flush()

        members = {}
        for name, email in (
            ("Email Eligible", "email-ok@example.test"),
            ("Suppressed", "suppressed@example.test"),
            ("Withdrawn", "withdrawn@example.test"),
            ("SMS Only", "sms-only@example.test"),
            ("No Basis", "no-basis@example.test"),
        ):
            member = AudienceMember(
                organization_id=org.id,
                full_name=name,
                email=email,
                preferred_language="en",
                status="active",
                created_by=user.id,
                updated_by=user.id,
            )
            session.add(member)
            session.flush()
            members[name] = member

        segment = AudienceSegment(
            organization_id=org.id,
            name="All active contacts",
            created_by=user.id,
        )
        session.add(segment)
        session.flush()
        filter_ast = {"field": "status", "operator": "eq", "value": "active"}
        segment_version = AudienceSegmentVersion(
            organization_id=org.id,
            segment_id=segment.id,
            version_number=1,
            filter_ast=filter_ast,
            filter_hash=content_sha256(filter_ast),
            created_by=user.id,
        )
        session.add(segment_version)
        session.flush()

        campaign = Campaign(
            organization_id=org.id,
            name="Mock public advisory",
            objective="Test eligibility evaluation",
            purpose_code="public_health_advisory",
            created_by=user.id,
        )
        session.add(campaign)
        session.flush()
        snapshot = {
            "purpose_code": "public_health_advisory",
            "channels": ["email", "sms"],
            "rendered_variants": {
                "email": {"en": "Email advisory"},
                "sms": {"en": "SMS advisory"},
            },
            "segment_version_id": str(segment_version.id),
        }
        version = CampaignVersion(
            organization_id=org.id,
            campaign_id=campaign.id,
            version_number=1,
            status="approved",
            purpose_code="public_health_advisory",
            channels=["email", "sms"],
            languages=["en"],
            content_snapshot=snapshot,
            content_hash=content_sha256(snapshot),
            segment_version_id=segment_version.id,
            created_by=user.id,
        )
        session.add(version)
        session.flush()
        session.add(
            CampaignApproval(
                organization_id=org.id,
                campaign_version_id=version.id,
                version_hash=version.content_hash,
                decision="approved",
                rationale="Independent test approval",
                decided_by=user.id,
            )
        )
        execution = CampaignExecution(
            organization_id=org.id,
            campaign_version_id=version.id,
            execution_mode="mock",
            status="queued",
            initiated_by=user.id,
        )
        session.add(execution)
        session.flush()

        for member in members.values():
            if member.full_name != "No Basis":
                session.add(
                    ProcessingBasisEvent(
                        organization_id=org.id,
                        audience_member_id=member.id,
                        purpose_code="public_health_advisory",
                        event_type="established",
                        basis_code="consent",
                        evidence_source="test_fixture",
                        recorded_by=user.id,
                        created_at=now,
                    )
                )

        for member_name, channel, decision in (
            ("Email Eligible", "email", "granted"),
            ("Suppressed", "email", "granted"),
            ("Withdrawn", "email", "withdrawn"),
            ("SMS Only", "sms", "granted"),
            ("No Basis", "email", "granted"),
        ):
            session.add(
                ChannelConsentEvent(
                    organization_id=org.id,
                    audience_member_id=members[member_name].id,
                    channel=channel,
                    purpose_code="public_health_advisory",
                    decision=decision,
                    evidence_source="test_fixture",
                    captured_at=now,
                    recorded_by=user.id,
                    created_at=now,
                )
            )
        session.add(
            SuppressionEvent(
                organization_id=org.id,
                audience_member_id=members["Suppressed"].id,
                channel="email",
                event_type="suppressed",
                reason_code="user_opt_out",
                source_code="test_fixture",
                recorded_by=user.id,
                created_at=now,
            )
        )
        execution_id = execution.id
        organization_id = org.id

    worker = MockCampaignWorker(factory, batch_size=2)
    result = worker.process(execution_id, organization_id)
    assert result["status"] == "completed"
    assert result["target_recipients"] == 5
    assert result["eligible_recipients"] == 2
    assert result["excluded_recipients"] == 3
    assert result["delivery_intents"] == 2
    assert result["accepted_count"] == 2

    with factory() as session:
        deliveries = list(
            session.scalars(
                select(ChannelDelivery).order_by(ChannelDelivery.channel)
            ).all()
        )
        attempts = list(session.scalars(select(DeliveryAttempt)).all())
        execution = session.get(CampaignExecution, execution_id)
        assert len(deliveries) == 2
        assert {delivery.channel for delivery in deliveries} == {"email", "sms"}
        assert all(delivery.simulated for delivery in deliveries)
        assert {delivery.status for delivery in deliveries} == {"simulated_accepted"}
        assert len(attempts) == 2
        assert all(attempt.simulated for attempt in attempts)
        assert execution.delivered_count == 0
        assert execution.accepted_count == 2

    # A redelivered outbox task must not create duplicate logical deliveries.
    replay = worker.process(execution_id, organization_id)
    assert replay["status"] == "completed"
    with factory() as session:
        assert session.scalar(select(func.count(ChannelDelivery.id))) == 2

    engine.dispose()
