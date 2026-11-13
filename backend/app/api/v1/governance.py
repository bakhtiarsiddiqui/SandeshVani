import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    AuthContext,
    TenantContext,
    get_current_user,
    require_permissions,
    verify_csrf,
    verify_origin,
)
from app.db.session import get_db
from app.models.governance import (
    AuditEvent,
    CampaignExecution,
    CampaignVersion,
    ChannelDelivery,
    ExecutionRecipient,
)
from app.schemas.governance import (
    ApprovalDecisionCreate,
    CampaignAnalyticsResponse,
    CampaignContentRevisionCreate,
    CampaignCreate,
    CampaignExecutionResponse,
    CampaignVersionCreate,
    ChannelConsentEventCreate,
    ProcessingBasisEventCreate,
    SegmentCreate,
    SegmentPreviewRequest,
    SegmentPreviewResponse,
    SegmentVersionCreate,
    SuppressionEventCreate,
    TemplateCreate,
    TemplateVersionCreate,
)
from app.services.governance_service import GovernanceService

router = APIRouter(prefix="/governance", tags=["Governance"])


@router.post(
    "/consent/processing-basis",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_origin), Depends(verify_csrf)],
)
async def create_processing_basis_event(
    data: ProcessingBasisEventCreate,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    tenant_ctx: Annotated[
        TenantContext, Depends(require_permissions("consent:update"))
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = GovernanceService(session, tenant_ctx.organization.id)
    event = await service.create_processing_basis(data.model_dump(), auth_ctx.user.id)
    await session.commit()
    return {
        "id": event.id,
        "audience_member_id": event.audience_member_id,
        "purpose_code": event.purpose_code,
        "event_type": event.event_type,
        "basis_code": event.basis_code,
        "created_at": event.created_at,
    }


@router.post(
    "/consent/channel-events",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_origin), Depends(verify_csrf)],
)
async def create_channel_consent_event(
    data: ChannelConsentEventCreate,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    tenant_ctx: Annotated[
        TenantContext, Depends(require_permissions("consent:update"))
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = GovernanceService(session, tenant_ctx.organization.id)
    event = await service.create_channel_consent_event(
        data.model_dump(), auth_ctx.user.id
    )
    await session.commit()
    return {
        "id": event.id,
        "audience_member_id": event.audience_member_id,
        "channel": event.channel,
        "purpose_code": event.purpose_code,
        "decision": event.decision,
        "captured_at": event.captured_at,
        "created_at": event.created_at,
    }


@router.post(
    "/consent/suppressions",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_origin), Depends(verify_csrf)],
)
async def create_suppression_event(
    data: SuppressionEventCreate,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    tenant_ctx: Annotated[
        TenantContext, Depends(require_permissions("suppression:update"))
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = GovernanceService(session, tenant_ctx.organization.id)
    event = await service.create_suppression_event(data.model_dump(), auth_ctx.user.id)
    await session.commit()
    return {
        "id": event.id,
        "audience_member_id": event.audience_member_id,
        "channel": event.channel,
        "event_type": event.event_type,
        "reason_code": event.reason_code,
        "created_at": event.created_at,
    }


@router.post(
    "/segments",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_origin), Depends(verify_csrf)],
)
async def create_segment(
    data: SegmentCreate,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    tenant_ctx: Annotated[
        TenantContext, Depends(require_permissions("segments:create"))
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = GovernanceService(session, tenant_ctx.organization.id)
    segment = await service.create_segment(data.model_dump(), auth_ctx.user.id)
    await session.commit()
    return {
        "id": segment.id,
        "name": segment.name,
        "description": segment.description,
        "status": segment.status,
    }


@router.post(
    "/segments/{segment_id}/versions",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_origin), Depends(verify_csrf)],
)
async def create_segment_version(
    segment_id: uuid.UUID,
    data: SegmentVersionCreate,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    tenant_ctx: Annotated[
        TenantContext, Depends(require_permissions("segments:update"))
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = GovernanceService(session, tenant_ctx.organization.id)
    version = await service.create_segment_version(segment_id, data, auth_ctx.user.id)
    await session.commit()
    return {
        "id": version.id,
        "segment_id": version.segment_id,
        "version_number": version.version_number,
        "filter_ast": version.filter_ast,
        "filter_hash": version.filter_hash,
    }


@router.post(
    "/segments/{segment_id}/preview",
    response_model=SegmentPreviewResponse,
)
async def preview_segment(
    segment_id: uuid.UUID,
    data: SegmentPreviewRequest,
    tenant_ctx: Annotated[TenantContext, Depends(require_permissions("segments:read"))],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = GovernanceService(session, tenant_ctx.organization.id)
    matched_count = await service.preview_segment(segment_id, data.version_id)
    return SegmentPreviewResponse(
        segment_id=segment_id,
        version_id=data.version_id,
        matched_count=matched_count,
    )


@router.post(
    "/templates",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_origin), Depends(verify_csrf)],
)
async def create_template(
    data: TemplateCreate,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    tenant_ctx: Annotated[
        TenantContext, Depends(require_permissions("templates:create"))
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = GovernanceService(session, tenant_ctx.organization.id)
    template = await service.create_template(data.model_dump(), auth_ctx.user.id)
    await session.commit()
    return {"id": template.id, "name": template.name, "status": template.status}


@router.post(
    "/templates/{template_id}/versions",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_origin), Depends(verify_csrf)],
)
async def create_template_version(
    template_id: uuid.UUID,
    data: TemplateVersionCreate,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    tenant_ctx: Annotated[
        TenantContext, Depends(require_permissions("templates:update"))
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = GovernanceService(session, tenant_ctx.organization.id)
    version = await service.create_template_version(template_id, data, auth_ctx.user.id)
    await session.commit()
    return {
        "id": version.id,
        "template_id": version.template_id,
        "version_number": version.version_number,
        "content_hash": version.content_hash,
        "variants": version.variants,
    }


@router.post(
    "/campaigns",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_origin), Depends(verify_csrf)],
)
async def create_campaign(
    data: CampaignCreate,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    tenant_ctx: Annotated[
        TenantContext, Depends(require_permissions("campaigns:create"))
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = GovernanceService(session, tenant_ctx.organization.id)
    campaign = await service.create_campaign(data.model_dump(), auth_ctx.user.id)
    await session.commit()
    return {
        "id": campaign.id,
        "name": campaign.name,
        "objective": campaign.objective,
        "purpose_code": campaign.purpose_code,
        "status": campaign.status,
    }


@router.post(
    "/campaigns/{campaign_id}/versions",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_origin), Depends(verify_csrf)],
)
async def create_campaign_version(
    campaign_id: uuid.UUID,
    data: CampaignVersionCreate,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    tenant_ctx: Annotated[
        TenantContext, Depends(require_permissions("campaigns:update"))
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = GovernanceService(session, tenant_ctx.organization.id)
    version = await service.create_campaign_version(campaign_id, data, auth_ctx.user.id)
    await session.commit()
    return {
        "id": version.id,
        "campaign_id": version.campaign_id,
        "version_number": version.version_number,
        "status": version.status,
        "content_hash": version.content_hash,
        "content_snapshot": version.content_snapshot,
    }


@router.post(
    "/campaigns/{campaign_id}/versions/{version_id}/content-revisions",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_origin), Depends(verify_csrf)],
)
async def create_campaign_content_revision(
    campaign_id: uuid.UUID,
    version_id: uuid.UUID,
    data: CampaignContentRevisionCreate,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    tenant_ctx: Annotated[
        TenantContext, Depends(require_permissions("campaigns:content:update"))
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = GovernanceService(session, tenant_ctx.organization.id)
    version = await service.create_content_revision(
        campaign_id, version_id, data, auth_ctx.user.id
    )
    await session.commit()
    return {
        "id": version.id,
        "campaign_id": version.campaign_id,
        "version_number": version.version_number,
        "status": version.status,
        "content_hash": version.content_hash,
        "content_snapshot": version.content_snapshot,
    }


@router.post(
    "/campaigns/{campaign_id}/versions/{version_id}/submit",
    dependencies=[Depends(verify_origin), Depends(verify_csrf)],
)
async def submit_campaign_version(
    campaign_id: uuid.UUID,
    version_id: uuid.UUID,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    tenant_ctx: Annotated[
        TenantContext, Depends(require_permissions("campaigns:submit"))
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = GovernanceService(session, tenant_ctx.organization.id)
    version = await service.submit_campaign_version(
        campaign_id, version_id, auth_ctx.user.id
    )
    await session.commit()
    return {
        "id": version.id,
        "status": version.status,
        "submitted_by": version.submitted_by,
        "submitted_at": version.submitted_at,
        "content_hash": version.content_hash,
    }


@router.post(
    "/campaigns/{campaign_id}/versions/{version_id}/approval",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_origin), Depends(verify_csrf)],
)
async def decide_campaign_approval(
    campaign_id: uuid.UUID,
    version_id: uuid.UUID,
    data: ApprovalDecisionCreate,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    tenant_ctx: Annotated[
        TenantContext, Depends(require_permissions("approvals:approve"))
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = GovernanceService(session, tenant_ctx.organization.id)
    version = await session.scalar(
        select(CampaignVersion).where(
            CampaignVersion.organization_id == tenant_ctx.organization.id,
            CampaignVersion.campaign_id == campaign_id,
            CampaignVersion.id == version_id,
        )
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Campaign version not found")
    approval = await service.approve_campaign_version(
        campaign_id,
        version_id,
        decision=data.decision,
        rationale=data.rationale,
        version_hash=version.content_hash,
        actor_id=auth_ctx.user.id,
    )
    await session.commit()
    return {
        "id": approval.id,
        "campaign_version_id": approval.campaign_version_id,
        "version_hash": approval.version_hash,
        "decision": approval.decision,
        "rationale": approval.rationale,
        "decided_by": approval.decided_by,
    }


@router.post(
    "/campaigns/{campaign_id}/versions/{version_id}/execute",
    response_model=CampaignExecutionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_origin), Depends(verify_csrf)],
)
async def enqueue_mock_campaign_execution(
    campaign_id: uuid.UUID,
    version_id: uuid.UUID,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    tenant_ctx: Annotated[
        TenantContext, Depends(require_permissions("distribution:mock_execute"))
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = GovernanceService(session, tenant_ctx.organization.id)
    execution = await service.enqueue_mock_execution(
        campaign_id, version_id, auth_ctx.user.id
    )
    await session.commit()
    return CampaignExecutionResponse.model_validate(execution)


@router.get(
    "/executions/{execution_id}/analytics",
    response_model=CampaignAnalyticsResponse,
)
async def get_campaign_execution_analytics(
    execution_id: uuid.UUID,
    tenant_ctx: Annotated[
        TenantContext, Depends(require_permissions("analytics:read"))
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    execution = await session.scalar(
        select(CampaignExecution).where(
            CampaignExecution.organization_id == tenant_ctx.organization.id,
            CampaignExecution.id == execution_id,
        )
    )
    if execution is None:
        raise HTTPException(status_code=404, detail="Campaign execution not found")
    rows = (
        await session.execute(
            select(
                ChannelDelivery.channel,
                ChannelDelivery.status,
                func.count(ChannelDelivery.id),
            )
            .where(
                ChannelDelivery.organization_id == tenant_ctx.organization.id,
                ChannelDelivery.recipient_id.in_(
                    select(ExecutionRecipient.id).where(
                        ExecutionRecipient.organization_id
                        == tenant_ctx.organization.id,
                        ExecutionRecipient.execution_id == execution_id,
                    )
                ),
            )
            .group_by(ChannelDelivery.channel, ChannelDelivery.status)
        )
    ).all()
    channel_data: dict[str, dict[str, int]] = {}
    for channel, delivery_status, count in rows:
        channel_data.setdefault(channel, {})[delivery_status] = int(count)
    return CampaignAnalyticsResponse(
        execution_id=execution.id,
        simulated=True,
        target_recipients=execution.target_recipients,
        eligible_recipients=execution.eligible_recipients,
        excluded_recipients=execution.excluded_recipients,
        delivery_intents=execution.delivery_intents,
        accepted=execution.accepted_count,
        delivered=execution.delivered_count,
        failed=execution.failed_count,
        retrying=execution.retrying_count,
        unknown=execution.unknown_count,
        channel_deliveries=channel_data,
    )


@router.get("/audit")
async def list_audit_events(
    tenant_ctx: Annotated[TenantContext, Depends(require_permissions("audit:read"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    rows = list(
        (
            await session.scalars(
                select(AuditEvent)
                .where(AuditEvent.organization_id == tenant_ctx.organization.id)
                .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
                .limit(limit)
            )
        ).all()
    )
    return {
        "data": [
            {
                "id": event.id,
                "actor_id": event.actor_id,
                "action": event.action,
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "event_data": event.event_data,
                "created_at": event.created_at,
            }
            for event in rows
        ]
    }
