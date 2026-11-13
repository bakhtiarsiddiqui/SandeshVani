import uuid
from collections.abc import Callable

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.audience_member import AudienceMember
from app.models.governance import (
    AuditEvent,
    AudienceSegmentVersion,
    CampaignApproval,
    CampaignExecution,
    CampaignVersion,
    ChannelConsentEvent,
    ChannelDelivery,
    DeliveryAttempt,
    ExecutionRecipient,
    ProcessingBasisEvent,
    SuppressionEvent,
)
from app.services.governance_service import content_sha256
from app.services.segment_filters import compile_segment_filter


def _set_tenant_context(session: Session, organization_id: uuid.UUID) -> None:
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        session.execute(
            text("SELECT set_config('app.current_org', :org_id, true)"),
            {"org_id": str(organization_id)},
        )


class MockCampaignWorker:
    """Execute an approved R1 campaign through a simulated-only adapter path."""

    def __init__(self, session_factory: Callable[[], Session], batch_size: int = 500):
        self.session_factory = session_factory
        self.batch_size = min(max(batch_size, 50), 1000)

    def mark_failed(
        self,
        execution_id: uuid.UUID,
        organization_id: uuid.UUID,
        error_code: str,
    ) -> None:
        with self.session_factory.begin() as session:
            _set_tenant_context(session, organization_id)
            execution = session.scalar(
                select(CampaignExecution)
                .where(
                    CampaignExecution.organization_id == organization_id,
                    CampaignExecution.id == execution_id,
                )
                .with_for_update()
            )
            if execution is not None and execution.status != "completed":
                execution.status = "failed"
                session.add(
                    AuditEvent(
                        organization_id=organization_id,
                        actor_id=execution.initiated_by,
                        action="campaign.mock_execution_failed",
                        entity_type="campaign_execution",
                        entity_id=execution.id,
                        event_data={"error_code": error_code, "simulated": True},
                    )
                )

    @staticmethod
    def _latest_value(model, *, organization_id, purpose_code=None, channel=None):
        if model is ProcessingBasisEvent:
            value_column = model.event_type
        elif model is ChannelConsentEvent:
            value_column = model.decision
        else:
            value_column = model.event_type
        query = select(value_column).where(
            model.organization_id == organization_id,
            model.audience_member_id == AudienceMember.id,
        )
        if purpose_code is not None and hasattr(model, "purpose_code"):
            query = query.where(model.purpose_code == purpose_code)
        if channel is not None:
            query = query.where(model.channel == channel)
        return (
            query.order_by(model.created_at.desc(), model.id.desc())
            .limit(1)
            .scalar_subquery()
        )

    def _eligible_member_ids(
        self,
        session,
        organization_id,
        purpose_code,
        channel,
        member_ids,
    ):
        if not member_ids:
            return []
        basis_latest = self._latest_value(
            ProcessingBasisEvent,
            organization_id=organization_id,
            purpose_code=purpose_code,
        )
        consent_latest = self._latest_value(
            ChannelConsentEvent,
            organization_id=organization_id,
            purpose_code=purpose_code,
            channel=channel,
        )
        suppression_latest = self._latest_value(
            SuppressionEvent,
            organization_id=organization_id,
            channel=channel,
        )
        query = select(AudienceMember.id).where(
            AudienceMember.organization_id == organization_id,
            AudienceMember.id.in_(member_ids),
            AudienceMember.status == "active",
            basis_latest == "established",
            consent_latest == "granted",
            func.coalesce(suppression_latest, "") != "suppressed",
        )
        return list(session.scalars(query).all())

    def process(self, execution_id: uuid.UUID, organization_id: uuid.UUID) -> dict:
        cursor = None
        with self.session_factory.begin() as session:
            _set_tenant_context(session, organization_id)
            execution = session.scalar(
                select(CampaignExecution)
                .where(
                    CampaignExecution.organization_id == organization_id,
                    CampaignExecution.id == execution_id,
                )
                .with_for_update()
            )
            if execution is None:
                return {"status": "not_found"}
            if execution.status == "completed":
                return {
                    "status": "completed",
                    "eligible_recipients": execution.eligible_recipients,
                }
            version = session.scalar(
                select(CampaignVersion).where(
                    CampaignVersion.organization_id == organization_id,
                    CampaignVersion.id == execution.campaign_version_id,
                )
            )
            if (
                version is None
                or version.status != "approved"
                or execution.execution_mode != "mock"
                or content_sha256(version.content_snapshot) != version.content_hash
            ):
                execution.status = "failed"
                return {
                    "status": "failed",
                    "error_code": "APPROVED_VERSION_INVALID",
                }
            approval_id = session.scalar(
                select(CampaignApproval.id).where(
                    CampaignApproval.organization_id == organization_id,
                    CampaignApproval.campaign_version_id == version.id,
                    CampaignApproval.decision == "approved",
                    CampaignApproval.version_hash == version.content_hash,
                )
            )
            segment = session.scalar(
                select(AudienceSegmentVersion).where(
                    AudienceSegmentVersion.organization_id == organization_id,
                    AudienceSegmentVersion.id == version.segment_version_id,
                )
            )
            if approval_id is None or segment is None:
                execution.status = "failed"
                return {
                    "status": "failed",
                    "error_code": "APPROVAL_OR_SEGMENT_MISSING",
                }
            filter_expression = compile_segment_filter(segment.filter_ast)
            execution.target_recipients = int(
                session.scalar(
                    select(func.count(AudienceMember.id)).where(
                        AudienceMember.organization_id == organization_id,
                        AudienceMember.status == "active",
                        filter_expression,
                    )
                )
                or 0
            )
            execution.status = "processing"
            purpose_code = version.purpose_code
            channels = list(version.channels)

        while True:
            with self.session_factory.begin() as session:
                _set_tenant_context(session, organization_id)
                execution = session.scalar(
                    select(CampaignExecution)
                    .where(
                        CampaignExecution.organization_id == organization_id,
                        CampaignExecution.id == execution_id,
                    )
                    .with_for_update()
                )
                if execution is None or execution.status == "failed":
                    return {"status": "failed"}
                if execution.status == "completed":
                    return {
                        "status": "completed",
                        "eligible_recipients": execution.eligible_recipients,
                    }
                version = session.scalar(
                    select(CampaignVersion).where(
                        CampaignVersion.organization_id == organization_id,
                        CampaignVersion.id == execution.campaign_version_id,
                    )
                )
                segment = session.scalar(
                    select(AudienceSegmentVersion).where(
                        AudienceSegmentVersion.organization_id == organization_id,
                        AudienceSegmentVersion.id == version.segment_version_id,
                    )
                )
                filter_expression = compile_segment_filter(segment.filter_ast)
                query = (
                    select(AudienceMember.id)
                    .where(
                        AudienceMember.organization_id == organization_id,
                        AudienceMember.status == "active",
                        filter_expression,
                    )
                    .order_by(AudienceMember.id.asc())
                    .limit(self.batch_size)
                )
                if cursor is not None:
                    query = query.where(AudienceMember.id > cursor)
                member_ids = list(session.scalars(query).all())
                if not member_ids:
                    execution.excluded_recipients = max(
                        0,
                        execution.target_recipients - execution.eligible_recipients,
                    )
                    execution.status = "completed"
                    session.add(
                        AuditEvent(
                            organization_id=organization_id,
                            actor_id=execution.initiated_by,
                            action="campaign.mock_execution_completed",
                            entity_type="campaign_execution",
                            entity_id=execution.id,
                            event_data={
                                "simulated": True,
                                "target_recipients": execution.target_recipients,
                                "eligible_recipients": execution.eligible_recipients,
                                "excluded_recipients": execution.excluded_recipients,
                                "delivery_intents": execution.delivery_intents,
                            },
                        )
                    )
                    return {
                        "status": "completed",
                        "target_recipients": execution.target_recipients,
                        "eligible_recipients": execution.eligible_recipients,
                        "excluded_recipients": execution.excluded_recipients,
                        "delivery_intents": execution.delivery_intents,
                        "accepted_count": execution.accepted_count,
                    }
                cursor = member_ids[-1]
                eligible_by_channel = {
                    channel: self._eligible_member_ids(
                        session,
                        organization_id,
                        purpose_code,
                        channel,
                        member_ids,
                    )
                    for channel in channels
                }
                eligible_union = sorted(
                    {
                        member_id
                        for ids in eligible_by_channel.values()
                        for member_id in ids
                    }
                )
                recipient_map = {}
                if eligible_union:
                    existing = session.execute(
                        select(
                            ExecutionRecipient.audience_member_id,
                            ExecutionRecipient.id,
                        ).where(
                            ExecutionRecipient.organization_id == organization_id,
                            ExecutionRecipient.execution_id == execution_id,
                            ExecutionRecipient.audience_member_id.in_(eligible_union),
                        )
                    ).all()
                    recipient_map = {
                        audience_id: recipient_id
                        for audience_id, recipient_id in existing
                    }
                new_recipients = [
                    ExecutionRecipient(
                        organization_id=organization_id,
                        execution_id=execution_id,
                        audience_member_id=member_id,
                    )
                    for member_id in eligible_union
                    if member_id not in recipient_map
                ]
                if new_recipients:
                    session.add_all(new_recipients)
                    session.flush()
                    recipient_map.update(
                        {
                            row.audience_member_id: row.id
                            for row in new_recipients
                        }
                    )
                    execution.eligible_recipients += len(new_recipients)
                new_deliveries = 0
                for channel, channel_ids in eligible_by_channel.items():
                    recipient_ids = [
                        recipient_map[item] for item in channel_ids
                    ]
                    if not recipient_ids:
                        continue
                    existing_delivery_ids = set(
                        session.scalars(
                            select(ChannelDelivery.recipient_id).where(
                                ChannelDelivery.organization_id == organization_id,
                                ChannelDelivery.recipient_id.in_(recipient_ids),
                                ChannelDelivery.channel == channel,
                            )
                        ).all()
                    )
                    for recipient_id in recipient_ids:
                        if recipient_id in existing_delivery_ids:
                            continue
                        delivery = ChannelDelivery(
                            organization_id=organization_id,
                            recipient_id=recipient_id,
                            channel=channel,
                            status="simulated_accepted",
                            simulated=True,
                        )
                        session.add(delivery)
                        session.flush()
                        session.add(
                            DeliveryAttempt(
                                organization_id=organization_id,
                                delivery_id=delivery.id,
                                attempt_number=1,
                                status="simulated_accepted",
                                simulated=True,
                            )
                        )
                        new_deliveries += 1
                execution.delivery_intents += new_deliveries
                execution.accepted_count += new_deliveries

        return {"status": "completed"}
