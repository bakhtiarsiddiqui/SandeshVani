"""AI Campaign Assistant router.

Endpoints:
  POST   /api/v1/ai/campaigns/generate          — generate drafts (service key)
  POST   /api/v1/ai/campaigns/{id}/approve      — approve/reject a draft (service key)
  GET    /api/v1/ai/campaigns/{id}              — retrieve request + draft (service key)

All endpoints require the X-API-Key header (service-to-service authentication).
No CSRF / origin check is applied — this is not a browser-facing endpoint.

The AI **never publishes** content. Drafts are saved with status=pending_approval.
Human approval via the /approve endpoint is required before any downstream use.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai.config import AISettings, get_ai_settings
from ai.models import (
    AIApprovalRecord,
    AIGeneratedContent,
    AIGenerationRequest,
    AIUsageLog,
)
from ai.pipeline import run_pipeline
from ai.providers.base import LLMProvider, ProviderError
from ai.providers.factory import build_provider
from ai.schemas import (
    ApprovalRequest,
    ApprovalResponse,
    CampaignBrief,
    GenerateResponse,
)
from ai.security import require_api_key
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Campaign Assistant"])


# ---------------------------------------------------------------------------
# Provider dependency — cached per process via lru_cache on AISettings
# ---------------------------------------------------------------------------


def get_provider(
    ai_settings: Annotated[AISettings, Depends(get_ai_settings)],
) -> LLMProvider:
    """Build the LLM provider chain once from validated settings."""
    return build_provider(ai_settings)


# ---------------------------------------------------------------------------
# DB writer used by the pipeline
# ---------------------------------------------------------------------------


def _make_db_writer(
    session: AsyncSession, organization_id: uuid.UUID, user_id: uuid.UUID | None
):
    async def _write(request_id, brief, draft, warnings):
        # Persist the generation request
        gen_req = AIGenerationRequest(
            id=request_id,
            organization_id=organization_id,
            requested_by_user_id=user_id,
            channel=brief.channel,
            language=brief.language,
            tone=brief.tone,
            key_facts=brief.key_facts.model_dump(),
            status="pending_approval",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(gen_req)

        # Persist the generated content
        content = AIGeneratedContent(
            id=uuid.uuid4(),
            request_id=request_id,
            organization_id=organization_id,
            draft_text=draft.text,
            char_count=draft.char_count,
            within_limit=draft.within_limit,
            provider=draft.provider,
            model=draft.model,
            validation_warnings=warnings,
            created_at=datetime.now(UTC),
        )
        session.add(content)

        # Persist usage log (token counts unknown for plain httpx calls)
        usage = AIUsageLog(
            id=uuid.uuid4(),
            request_id=request_id,
            organization_id=organization_id,
            provider=draft.provider,
            model=draft.model,
            success=True,
            logged_at=datetime.now(UTC),
        )
        session.add(usage)

        await session.flush()

    return _write


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/campaigns/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_api_key)],
    summary="Generate AI campaign message drafts",
    description=(
        "Accepts a structured campaign brief, generates drafts using a free-tier "
        "LLM, validates them, and saves them with status=pending_approval. "
        "The AI never publishes. Human approval is required before use."
    ),
)
async def generate_campaign_drafts(
    brief: CampaignBrief,
    session: Annotated[AsyncSession, Depends(get_db)],
    provider: Annotated[LLMProvider, Depends(get_provider)],
) -> GenerateResponse:
    request_id = uuid.uuid4()

    organization_id = brief.organization_id

    db_writer = _make_db_writer(session, organization_id, user_id=None)

    try:
        final_state = await run_pipeline(
            brief=brief,
            provider=provider,
            db_writer=db_writer,
            request_id=request_id,
        )
    except ProviderError as exc:
        logger.error("Provider error during generation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM provider error: {exc}",
        ) from exc

    if not final_state.get("persisted"):
        logger.error("Draft persistence failed: %s", final_state.get("error"))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist generated draft.",
        )

    await session.commit()

    draft = final_state["draft"]
    warnings = final_state.get("validation_warnings", [])

    return GenerateResponse(
        request_id=request_id,
        status="pending_approval",
        drafts=[draft],
        validation_warnings=warnings,
    )


@router.get(
    "/campaigns/{request_id}",
    dependencies=[Depends(require_api_key)],
    summary="Retrieve a generation request and its draft",
)
async def get_generation_request(
    request_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    from sqlalchemy import select  # noqa: PLC0415

    result = await session.execute(
        select(AIGenerationRequest).where(AIGenerationRequest.id == request_id)
    )
    gen_req = result.scalar_one_or_none()
    if not gen_req:
        raise HTTPException(status_code=404, detail="Generation request not found")

    content_result = await session.execute(
        select(AIGeneratedContent).where(AIGeneratedContent.request_id == request_id)
    )
    content = content_result.scalar_one_or_none()

    return {
        "request_id": gen_req.id,
        "status": gen_req.status,
        "channel": gen_req.channel,
        "language": gen_req.language,
        "tone": gen_req.tone,
        "key_facts": gen_req.key_facts,
        "created_at": gen_req.created_at,
        "draft": {
            "text": content.draft_text if content else None,
            "char_count": content.char_count if content else None,
            "within_limit": content.within_limit if content else None,
            "provider": content.provider if content else None,
            "model": content.model if content else None,
            "validation_warnings": content.validation_warnings if content else [],
        },
    }


@router.post(
    "/campaigns/{request_id}/approve",
    response_model=ApprovalResponse,
    dependencies=[Depends(require_api_key)],
    summary="Approve or reject a pending AI-generated draft",
    description=(
        "Records a human approve/reject decision. "
        "Approved drafts may then be used as campaign content. "
        "This endpoint never triggers distribution."
    ),
)
async def approve_generation_request(
    request_id: uuid.UUID,
    body: ApprovalRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApprovalResponse:
    from sqlalchemy import select, update  # noqa: PLC0415

    result = await session.execute(
        select(AIGenerationRequest).where(AIGenerationRequest.id == request_id)
    )
    gen_req = result.scalar_one_or_none()
    if not gen_req:
        raise HTTPException(status_code=404, detail="Generation request not found")

    if gen_req.status != "pending_approval":
        raise HTTPException(
            status_code=400,
            detail=f"Request is already in status '{gen_req.status}'.",
        )

    new_status = "approved" if body.action == "approve" else "rejected"

    # Update the request status
    await session.execute(
        update(AIGenerationRequest)
        .where(AIGenerationRequest.id == request_id)
        .values(status=new_status, updated_at=datetime.now(UTC))
    )

    # Record the approval decision
    record = AIApprovalRecord(
        id=uuid.uuid4(),
        request_id=request_id,
        organization_id=gen_req.organization_id,
        reviewer_user_id=None,  # service-to-service; no user session in this endpoint
        action=body.action,
        reviewer_note=body.reviewer_note,
        decided_at=datetime.now(UTC),
    )
    session.add(record)
    await session.commit()

    return ApprovalResponse(
        request_id=request_id,
        action=body.action,
        status=new_status,
        reviewer_note=body.reviewer_note,
    )
