from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import AuthContext, get_current_user
from app.db.session import get_db
from app.models.role import PlatformRoleAssignment, Role
from app.repositories.role_repo import RoleRepository
from app.schemas.organization import RoleResponse

router = APIRouter(prefix="/platform", tags=["Platform"])


@router.get("/me")
async def get_my_platform_role_context(
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Return only the authenticated user's separately assigned platform roles."""
    result = await session.execute(
        select(PlatformRoleAssignment)
        .where(PlatformRoleAssignment.user_id == auth_ctx.user.id)
        .options(
            selectinload(PlatformRoleAssignment.role).selectinload(Role.permissions)
        )
    )
    assignments = result.scalars().all()
    roles = [assignment.role for assignment in assignments]
    permissions = await RoleRepository(session).get_permissions_for_roles(
        [role.id for role in roles]
    )
    return {
        "platform_roles": [RoleResponse.model_validate(role) for role in roles],
        "platform_permissions": permissions,
    }
