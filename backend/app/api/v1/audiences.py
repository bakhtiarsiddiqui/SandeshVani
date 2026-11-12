import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    AuthContext,
    TenantContext,
    get_current_user,
    require_permissions,
    verify_csrf,
    verify_origin,
)
from app.core.http_status import HTTP_422_UNPROCESSABLE_CONTENT
from app.db.session import get_db
from app.schemas.audience import (
    AudienceMemberCreate,
    AudienceMemberListResponse,
    AudienceMemberResponse,
    AudienceMemberUpdate,
    AudiencePagination,
)
from app.services.audience_service import AudienceService

router = APIRouter(prefix="/audiences", tags=["Audiences"])


@router.get("", response_model=AudienceMemberListResponse)
async def list_audience_members(
    tenant_ctx: Annotated[
        TenantContext, Depends(require_permissions("audiences:read"))
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    status_filter: Annotated[
        Literal["active", "inactive"] | None, Query(alias="status")
    ] = None,
    district: Annotated[str | None, Query(max_length=150)] = None,
    language: Annotated[Literal["en", "hi"] | None, Query()] = None,
):
    if search is not None and not search.strip():
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail="search must not be blank",
        )
    if district is not None and not district.strip():
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail="district must not be blank",
        )

    service = AudienceService(session, tenant_ctx.organization.id)
    members, has_more, next_cursor = await service.list_members(
        limit=limit,
        cursor=cursor,
        search=search.strip() if search is not None else None,
        status=status_filter,
        district=district.strip() if district is not None else None,
        language=language,
    )
    return AudienceMemberListResponse(
        data=[AudienceMemberResponse.model_validate(member) for member in members],
        pagination=AudiencePagination(
            next_cursor=next_cursor,
            has_more=has_more,
            limit=limit,
        ),
    )


@router.post(
    "",
    response_model=AudienceMemberResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_origin), Depends(verify_csrf)],
)
async def create_audience_member(
    data: AudienceMemberCreate,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    tenant_ctx: Annotated[
        TenantContext, Depends(require_permissions("audiences:create"))
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = AudienceService(session, tenant_ctx.organization.id)
    member = await service.create_member(
        values=data.model_dump(),
        actor_user_id=auth_ctx.user.id,
    )
    await session.commit()
    await session.refresh(member)
    return AudienceMemberResponse.model_validate(member)


@router.get("/{audience_id}", response_model=AudienceMemberResponse)
async def get_audience_member(
    audience_id: uuid.UUID,
    tenant_ctx: Annotated[
        TenantContext, Depends(require_permissions("audiences:read"))
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = AudienceService(session, tenant_ctx.organization.id)
    member = await service.get_member(audience_id)
    return AudienceMemberResponse.model_validate(member)


@router.patch(
    "/{audience_id}",
    response_model=AudienceMemberResponse,
    dependencies=[Depends(verify_origin), Depends(verify_csrf)],
)
async def update_audience_member(
    audience_id: uuid.UUID,
    data: AudienceMemberUpdate,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    tenant_ctx: Annotated[
        TenantContext, Depends(require_permissions("audiences:update"))
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    if not data.model_fields_set:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be supplied",
        )
    service = AudienceService(session, tenant_ctx.organization.id)
    member = await service.update_member(
        member_id=audience_id,
        values=data.model_dump(exclude_unset=True),
        actor_user_id=auth_ctx.user.id,
    )
    await session.commit()
    await session.refresh(member)
    return AudienceMemberResponse.model_validate(member)
