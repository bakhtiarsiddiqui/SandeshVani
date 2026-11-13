import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    AuthContext,
    TenantContext,
    get_current_user,
    get_tenant_context,
    require_permissions,
    verify_csrf,
    verify_origin,
)
from app.db.session import get_db, set_tenant_context
from app.schemas.organization import (
    MemberAddRequest,
    MembershipResponse,
    OrganizationCreate,
    OrganizationResponse,
    PermissionResponse,
    RoleAssignRequest,
    RoleResponse,
)
from app.schemas.user import UserResponse
from app.services.organization_service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.get("", response_model=list[OrganizationResponse])
async def list_user_organizations(
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = OrganizationService(session)
    orgs = await service.get_user_organizations(auth_ctx.user.id)
    return [OrganizationResponse.model_validate(o) for o in orgs]


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_origin)],
)
async def create_organization(
    data: OrganizationCreate,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = OrganizationService(session)
    # create_organization commits atomically; do not commit again here
    org = await service.create_organization(
        name=data.name,
        slug=data.slug,
        creator_user_id=auth_ctx.user.id,
    )
    return OrganizationResponse.model_validate(org)


@router.get("/current", response_model=OrganizationResponse)
async def get_current_organization(
    tenant_ctx: Annotated[TenantContext, Depends(get_tenant_context)],
):
    return OrganizationResponse.model_validate(tenant_ctx.organization)


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: uuid.UUID,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = OrganizationService(session)
    org = await service.get_organization(organization_id, auth_ctx.user.id)
    return OrganizationResponse.model_validate(org)


@router.get(
    "/{organization_id}/members",
    response_model=list[MembershipResponse],
    dependencies=[Depends(require_permissions("members:read"))],
)
async def get_organization_members(
    organization_id: uuid.UUID,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = OrganizationService(session)
    memberships = await service.get_organization_members(
        organization_id, auth_ctx.user.id
    )

    results: list[MembershipResponse] = []
    for m in memberships:
        roles = []
        for mr in m.membership_roles:
            if mr.role:
                roles.append(RoleResponse.model_validate(mr.role))
        results.append(
            MembershipResponse(
                id=m.id,
                organization_id=m.organization_id,
                user_id=m.user_id,
                status=m.status,
                joined_at=m.joined_at,
                user=UserResponse.model_validate(m.user) if m.user else None,
                roles=roles,
            )
        )
    return results


@router.post(
    "/{organization_id}/members",
    response_model=MembershipResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(verify_origin),
        Depends(verify_csrf),
        Depends(require_permissions("members:create")),
    ],
)
async def add_organization_member(
    organization_id: uuid.UUID,
    data: MemberAddRequest,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = OrganizationService(session)
    membership = await service.add_member(
        organization_id=organization_id,
        actor_user_id=auth_ctx.user.id,
        email=data.email,
        role_ids=data.role_ids,
    )
    await session.commit()
    # Restore transaction-local RLS context before loading tenant-scoped roles.
    await set_tenant_context(session, organization_id)

    roles = []
    for r_id in data.role_ids:
        r = await service.role_repo.get_role_by_id(r_id)
        if r:
            roles.append(RoleResponse.model_validate(r))

    user = await service.user_repo.get_by_id(membership.user_id)

    return MembershipResponse(
        id=membership.id,
        organization_id=membership.organization_id,
        user_id=membership.user_id,
        status=membership.status,
        joined_at=membership.joined_at,
        user=UserResponse.model_validate(user) if user else None,
        roles=roles,
    )


@router.get(
    "/{organization_id}/roles",
    response_model=list[RoleResponse],
    dependencies=[Depends(require_permissions("roles:read"))],
)
async def list_organization_roles(
    organization_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = OrganizationService(session)
    roles = await service.role_repo.get_organization_roles(organization_id)
    return [RoleResponse.model_validate(r) for r in roles]


@router.post(
    "/{organization_id}/members/{membership_id}/roles",
    dependencies=[
        Depends(verify_origin),
        Depends(verify_csrf),
        Depends(require_permissions("roles:assign")),
    ],
)
async def assign_role(
    organization_id: uuid.UUID,
    membership_id: uuid.UUID,
    data: RoleAssignRequest,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = OrganizationService(session)
    await service.assign_role_to_member(
        organization_id=organization_id,
        actor_user_id=auth_ctx.user.id,
        membership_id=membership_id,
        role_id=data.role_id,
    )
    await session.commit()
    return {"message": "Role assigned successfully"}


@router.delete(
    "/{organization_id}/members/{membership_id}/roles/{role_id}",
    dependencies=[
        Depends(verify_origin),
        Depends(verify_csrf),
        Depends(require_permissions("roles:assign")),
    ],
)
async def remove_role(
    organization_id: uuid.UUID,
    membership_id: uuid.UUID,
    role_id: uuid.UUID,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = OrganizationService(session)
    await service.remove_role_from_member(
        organization_id=organization_id,
        actor_user_id=auth_ctx.user.id,
        membership_id=membership_id,
        role_id=role_id,
    )
    await session.commit()
    return {"message": "Role removed successfully"}


@router.get(
    "/{organization_id}/permissions",
    response_model=list[PermissionResponse],
    dependencies=[Depends(require_permissions("permissions:read"))],
)
async def list_permissions(
    organization_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    from sqlalchemy import select

    from app.models.role import Permission

    result = await session.execute(select(Permission).order_by(Permission.code))
    perms = list(result.scalars().all())
    return [PermissionResponse.model_validate(p) for p in perms]
