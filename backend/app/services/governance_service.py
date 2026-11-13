"""R1 tenant-scoped governance workflows and audit recording."""

import hashlib
import json
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audience_member import AudienceMember
from app.models.governance import (
    AudienceSegment,
    AudienceSegmentVersion,
    AuditEvent,
    Campaign,
    CampaignApproval,
    CampaignExecution,
    CampaignVersion,
    ChannelConsentEvent,
    MessageTemplate,
    MessageTemplateVersion,
    ProcessingBasisEvent,
    SuppressionEvent,
)
from app.models.outbox_event import OutboxEvent
from app.schemas.governance import (
    CampaignContentRevisionCreate,
    CampaignVersionCreate,
    SegmentVersionCreate,
    TemplateVersionCreate,
)
from app.services.segment_filters import (
    compile_segment_filter,
    validate_segment_filter,
)


def canonical_json(value: dict) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def content_sha256(value: dict) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class GovernanceService:
    def __init__(self, session: AsyncSession, organization_id: uuid.UUID):
        self.session = session
        self.organization_id = organization_id

    async def _audit(
        self,
        *,
        actor_id: uuid.UUID | None,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID | None,
        event_data: dict | None = None,
    ) -> None:
        """Write metadata-only audit evidence in the same transaction."""
        self.session.add(
            AuditEvent(
                organization_id=self.organization_id,
                actor_id=actor_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                event_data=event_data or {},
            )
        )
        await self.session.flush()

    async def _require_audience(self, audience_member_id: uuid.UUID) -> AudienceMember:
        member = await self.session.scalar(
            select(AudienceMember).where(
                AudienceMember.organization_id == self.organization_id,
                AudienceMember.id == audience_member_id,
            )
        )
        if member is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audience member not found",
            )
        return member

    async def create_processing_basis(
        self,
        values: dict,
        actor_id: uuid.UUID,
    ) -> ProcessingBasisEvent:
        await self._require_audience(values["audience_member_id"])
        event = ProcessingBasisEvent(
            organization_id=self.organization_id,
            recorded_by=actor_id,
            **values,
        )
        self.session.add(event)
        await self.session.flush()
        await self._audit(
            actor_id=actor_id,
            action=f"processing_basis.{event.event_type}",
            entity_type="audience_member",
            entity_id=event.audience_member_id,
            event_data={
                "purpose_code": event.purpose_code,
                "basis_code": event.basis_code,
                "event_id": str(event.id),
            },
        )
        return event

    async def create_channel_consent_event(
        self,
        values: dict,
        actor_id: uuid.UUID,
    ) -> ChannelConsentEvent:
        await self._require_audience(values["audience_member_id"])
        event = ChannelConsentEvent(
            organization_id=self.organization_id,
            recorded_by=actor_id,
            captured_at=datetime.now(UTC),
            **values,
        )
        self.session.add(event)
        await self.session.flush()
        await self._audit(
            actor_id=actor_id,
            action=f"channel_consent.{event.decision}",
            entity_type="audience_member",
            entity_id=event.audience_member_id,
            event_data={
                "channel": event.channel,
                "purpose_code": event.purpose_code,
                "event_id": str(event.id),
            },
        )
        return event

    async def create_suppression_event(
        self,
        values: dict,
        actor_id: uuid.UUID,
    ) -> SuppressionEvent:
        await self._require_audience(values["audience_member_id"])
        event = SuppressionEvent(
            organization_id=self.organization_id,
            recorded_by=actor_id,
            **values,
        )
        self.session.add(event)
        await self.session.flush()
        await self._audit(
            actor_id=actor_id,
            action=f"suppression.{event.event_type}",
            entity_type="audience_member",
            entity_id=event.audience_member_id,
            event_data={
                "channel": event.channel,
                "reason_code": event.reason_code,
                "event_id": str(event.id),
            },
        )
        return event

    async def create_segment(
        self,
        values: dict,
        actor_id: uuid.UUID,
    ) -> AudienceSegment:
        segment = AudienceSegment(
            organization_id=self.organization_id,
            created_by=actor_id,
            **values,
        )
        self.session.add(segment)
        await self.session.flush()
        await self._audit(
            actor_id=actor_id,
            action="segment.created",
            entity_type="audience_segment",
            entity_id=segment.id,
        )
        return segment

    async def create_segment_version(
        self,
        segment_id: uuid.UUID,
        values: SegmentVersionCreate,
        actor_id: uuid.UUID,
    ) -> AudienceSegmentVersion:
        segment = await self.session.scalar(
            select(AudienceSegment).where(
                AudienceSegment.organization_id == self.organization_id,
                AudienceSegment.id == segment_id,
            )
        )
        if segment is None or segment.status != "active":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audience segment not found",
            )
        try:
            safe_filter = validate_segment_filter(values.filter_ast)
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from error
        current_number = await self.session.scalar(
            select(func.max(AudienceSegmentVersion.version_number)).where(
                AudienceSegmentVersion.organization_id == self.organization_id,
                AudienceSegmentVersion.segment_id == segment_id,
            )
        )
        version = AudienceSegmentVersion(
            organization_id=self.organization_id,
            segment_id=segment_id,
            version_number=(current_number or 0) + 1,
            filter_ast=safe_filter,
            filter_hash=content_sha256(safe_filter),
            created_by=actor_id,
        )
        self.session.add(version)
        await self.session.flush()
        await self._audit(
            actor_id=actor_id,
            action="segment.version_created",
            entity_type="audience_segment_version",
            entity_id=version.id,
            event_data={
                "segment_id": str(segment_id),
                "version_number": version.version_number,
            },
        )
        return version

    async def preview_segment(
        self,
        segment_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> int:
        version = await self.session.scalar(
            select(AudienceSegmentVersion).where(
                AudienceSegmentVersion.organization_id == self.organization_id,
                AudienceSegmentVersion.segment_id == segment_id,
                AudienceSegmentVersion.id == version_id,
            )
        )
        if version is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Segment version not found",
            )
        expression = compile_segment_filter(version.filter_ast)
        matched = await self.session.scalar(
            select(func.count(AudienceMember.id)).where(
                AudienceMember.organization_id == self.organization_id,
                AudienceMember.status == "active",
                expression,
            )
        )
        return int(matched or 0)

    async def create_template(
        self,
        values: dict,
        actor_id: uuid.UUID,
    ) -> MessageTemplate:
        template = MessageTemplate(
            organization_id=self.organization_id,
            created_by=actor_id,
            **values,
        )
        self.session.add(template)
        await self.session.flush()
        await self._audit(
            actor_id=actor_id,
            action="template.created",
            entity_type="message_template",
            entity_id=template.id,
        )
        return template

    async def create_template_version(
        self,
        template_id: uuid.UUID,
        values: TemplateVersionCreate,
        actor_id: uuid.UUID,
    ) -> MessageTemplateVersion:
        template = await self.session.scalar(
            select(MessageTemplate).where(
                MessageTemplate.organization_id == self.organization_id,
                MessageTemplate.id == template_id,
                MessageTemplate.status == "active",
            )
        )
        if template is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message template not found",
            )
        current_number = await self.session.scalar(
            select(func.max(MessageTemplateVersion.version_number)).where(
                MessageTemplateVersion.organization_id == self.organization_id,
                MessageTemplateVersion.template_id == template_id,
            )
        )
        version = MessageTemplateVersion(
            organization_id=self.organization_id,
            template_id=template_id,
            version_number=(current_number or 0) + 1,
            variants=values.variants,
            content_hash=content_sha256(values.variants),
            created_by=actor_id,
        )
        self.session.add(version)
        await self.session.flush()
        await self._audit(
            actor_id=actor_id,
            action="template.version_created",
            entity_type="message_template_version",
            entity_id=version.id,
            event_data={
                "template_id": str(template_id),
                "version_number": version.version_number,
            },
        )
        return version

    async def create_campaign(
        self,
        values: dict,
        actor_id: uuid.UUID,
    ) -> Campaign:
        campaign = Campaign(
            organization_id=self.organization_id,
            created_by=actor_id,
            **values,
        )
        self.session.add(campaign)
        await self.session.flush()
        await self._audit(
            actor_id=actor_id,
            action="campaign.created",
            entity_type="campaign",
            entity_id=campaign.id,
        )
        return campaign

    async def _campaign(self, campaign_id: uuid.UUID) -> Campaign:
        campaign = await self.session.scalar(
            select(Campaign).where(
                Campaign.organization_id == self.organization_id,
                Campaign.id == campaign_id,
            )
        )
        if campaign is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found",
            )
        return campaign

    async def create_campaign_version(
        self,
        campaign_id: uuid.UUID,
        values: CampaignVersionCreate,
        actor_id: uuid.UUID,
    ) -> CampaignVersion:
        campaign = await self._campaign(campaign_id)
        segment = await self.session.scalar(
            select(AudienceSegmentVersion).where(
                AudienceSegmentVersion.organization_id == self.organization_id,
                AudienceSegmentVersion.id == values.segment_version_id,
            )
        )
        if segment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected segment version not found",
            )

        template = None
        if values.template_version_id:
            template = await self.session.scalar(
                select(MessageTemplateVersion).where(
                    MessageTemplateVersion.organization_id == self.organization_id,
                    MessageTemplateVersion.id == values.template_version_id,
                )
            )
            if template is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Selected template version not found",
                )
            for channel in values.channels:
                if channel not in template.variants:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=f"Template version has no explicit {channel} variant",
                    )
                missing = set(values.languages) - set(template.variants[channel])
                if missing:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=(
                            "Template version is missing explicit languages "
                            f"for {channel}"
                        ),
                    )

        current_number = await self.session.scalar(
            select(func.max(CampaignVersion.version_number)).where(
                CampaignVersion.organization_id == self.organization_id,
                CampaignVersion.campaign_id == campaign_id,
            )
        )
        snapshot = {
            "campaign": {
                "name": campaign.name,
                "objective": campaign.objective,
            },
            "purpose_code": campaign.purpose_code,
            "channels": list(values.channels),
            "languages": list(values.languages),
            "segment_version_id": str(segment.id),
            "segment_filter_hash": segment.filter_hash,
            "template_version_id": str(template.id) if template else None,
            "template_content_hash": template.content_hash if template else None,
            "rendered_variants": values.rendered_variants,
        }
        version = CampaignVersion(
            organization_id=self.organization_id,
            campaign_id=campaign_id,
            version_number=(current_number or 0) + 1,
            status="draft",
            purpose_code=campaign.purpose_code,
            channels=list(values.channels),
            languages=list(values.languages),
            content_snapshot=snapshot,
            content_hash=content_sha256(snapshot),
            template_version_id=template.id if template else None,
            segment_version_id=segment.id,
            created_by=actor_id,
        )
        self.session.add(version)
        campaign.status = "draft"
        await self.session.flush()
        await self._audit(
            actor_id=actor_id,
            action="campaign.version_created",
            entity_type="campaign_version",
            entity_id=version.id,
            event_data={
                "campaign_id": str(campaign_id),
                "version_number": version.version_number,
            },
        )
        return version

    async def create_content_revision(
        self,
        campaign_id: uuid.UUID,
        source_version_id: uuid.UUID,
        values: CampaignContentRevisionCreate,
        actor_id: uuid.UUID,
    ) -> CampaignVersion:
        campaign = await self._campaign(campaign_id)
        source = await self.session.scalar(
            select(CampaignVersion).where(
                CampaignVersion.organization_id == self.organization_id,
                CampaignVersion.campaign_id == campaign_id,
                CampaignVersion.id == source_version_id,
            )
        )
        if source is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign version not found",
            )
        for channel in source.channels:
            if channel not in values.rendered_variants:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"An explicit {channel} content variant is required",
                )
            missing = set(source.languages) - set(values.rendered_variants[channel])
            if missing:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Missing explicit language variants for {channel}",
                )
        current_number = await self.session.scalar(
            select(func.max(CampaignVersion.version_number)).where(
                CampaignVersion.organization_id == self.organization_id,
                CampaignVersion.campaign_id == campaign_id,
            )
        )
        snapshot = dict(source.content_snapshot)
        snapshot["rendered_variants"] = values.rendered_variants
        version = CampaignVersion(
            organization_id=self.organization_id,
            campaign_id=campaign_id,
            version_number=(current_number or 0) + 1,
            status="draft",
            purpose_code=source.purpose_code,
            channels=list(source.channels),
            languages=list(source.languages),
            content_snapshot=snapshot,
            content_hash=content_sha256(snapshot),
            template_version_id=source.template_version_id,
            segment_version_id=source.segment_version_id,
            created_by=actor_id,
        )
        self.session.add(version)
        campaign.status = "draft"
        await self.session.flush()
        await self._audit(
            actor_id=actor_id,
            action="campaign.content_revision_created",
            entity_type="campaign_version",
            entity_id=version.id,
            event_data={
                "campaign_id": str(campaign_id),
                "source_version_id": str(source.id),
            },
        )
        return version

    async def submit_campaign_version(
        self,
        campaign_id: uuid.UUID,
        version_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> CampaignVersion:
        campaign = await self._campaign(campaign_id)
        version = await self.session.scalar(
            select(CampaignVersion).where(
                CampaignVersion.organization_id == self.organization_id,
                CampaignVersion.campaign_id == campaign_id,
                CampaignVersion.id == version_id,
            )
        )
        if version is None or version.status != "draft":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only a draft campaign version can be submitted",
            )
        if content_sha256(version.content_snapshot) != version.content_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Campaign version content hash verification failed",
            )
        version.status = "submitted"
        version.submitted_by = actor_id
        version.submitted_at = datetime.now(UTC)
        campaign.status = "submitted"
        await self.session.flush()
        await self._audit(
            actor_id=actor_id,
            action="campaign.version_submitted",
            entity_type="campaign_version",
            entity_id=version.id,
            event_data={
                "campaign_id": str(campaign_id),
                "content_hash": version.content_hash,
            },
        )
        return version

    async def approve_campaign_version(
        self,
        campaign_id: uuid.UUID,
        version_id: uuid.UUID,
        *,
        decision: str,
        rationale: str,
        version_hash: str,
        actor_id: uuid.UUID,
    ) -> CampaignApproval:
        campaign = await self._campaign(campaign_id)
        version = await self.session.scalar(
            select(CampaignVersion).where(
                CampaignVersion.organization_id == self.organization_id,
                CampaignVersion.campaign_id == campaign_id,
                CampaignVersion.id == version_id,
            )
        )
        if version is None or version.status != "submitted":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only a submitted campaign version can be reviewed",
            )
        if actor_id in {version.created_by, version.submitted_by}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Campaign creator or submitter cannot approve their version",
            )
        if (
            version_hash != version.content_hash
            or content_sha256(version.content_snapshot) != version.content_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Approval must reference the exact submitted version hash",
            )
        existing = await self.session.scalar(
            select(CampaignApproval.id).where(
                CampaignApproval.organization_id == self.organization_id,
                CampaignApproval.campaign_version_id == version_id,
            )
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This campaign version already has a recorded approval decision",
            )
        approval = CampaignApproval(
            organization_id=self.organization_id,
            campaign_version_id=version_id,
            version_hash=version_hash,
            decision=decision,
            rationale=rationale.strip(),
            decided_by=actor_id,
        )
        self.session.add(approval)
        version.status = "approved" if decision == "approved" else "changes_requested"
        campaign.status = version.status
        await self.session.flush()
        await self._audit(
            actor_id=actor_id,
            action=f"campaign.version_{decision}",
            entity_type="campaign_version",
            entity_id=version_id,
            event_data={"content_hash": version_hash, "approval_id": str(approval.id)},
        )
        return approval

    async def enqueue_mock_execution(
        self,
        campaign_id: uuid.UUID,
        version_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> CampaignExecution:
        version = await self.session.scalar(
            select(CampaignVersion).where(
                CampaignVersion.organization_id == self.organization_id,
                CampaignVersion.campaign_id == campaign_id,
                CampaignVersion.id == version_id,
            )
        )
        if version is None or version.status != "approved":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only an approved immutable campaign version can execute",
            )
        if content_sha256(version.content_snapshot) != version.content_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Campaign version content hash verification failed",
            )
        approval = await self.session.scalar(
            select(CampaignApproval).where(
                CampaignApproval.organization_id == self.organization_id,
                CampaignApproval.campaign_version_id == version_id,
                CampaignApproval.decision == "approved",
                CampaignApproval.version_hash == version.content_hash,
            )
        )
        if approval is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="A matching independent approval is required",
            )
        execution = CampaignExecution(
            organization_id=self.organization_id,
            campaign_version_id=version_id,
            execution_mode="mock",
            status="queued",
            initiated_by=actor_id,
        )
        self.session.add(execution)
        await self.session.flush()
        self.session.add(
            OutboxEvent(
                organization_id=self.organization_id,
                aggregate_type="campaign_execution",
                aggregate_id=execution.id,
                event_type="campaign.mock_execute.queued",
                payload={
                    "execution_id": str(execution.id),
                    "campaign_version_id": str(version_id),
                },
            )
        )
        await self._audit(
            actor_id=actor_id,
            action="campaign.mock_execution_queued",
            entity_type="campaign_execution",
            entity_id=execution.id,
            event_data={
                "campaign_version_id": str(version_id),
                "simulated": True,
            },
        )
        await self.session.flush()
        return execution
