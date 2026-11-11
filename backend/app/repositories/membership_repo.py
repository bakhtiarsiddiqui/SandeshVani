import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.membership import Membership
from app.models.role import MembershipRole, Role


class MembershipRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_membership(
        self, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> Membership | None:
        stmt = (
            select(Membership)
            .where(
                Membership.organization_id == organization_id,
                Membership.user_id == user_id,
            )
            .options(selectinload(Membership.membership_roles))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_membership_by_id(self, membership_id: uuid.UUID) -> Membership | None:
        stmt = (
            select(Membership)
            .where(Membership.id == membership_id)
            .options(selectinload(Membership.membership_roles))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_membership(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        status: str = "active",
    ) -> Membership:
        membership = Membership(
            organization_id=organization_id,
            user_id=user_id,
            status=status,
        )
        self.session.add(membership)
        await self.session.flush()
        return membership

    async def get_organization_members(
        self, organization_id: uuid.UUID
    ) -> list[Membership]:
        stmt = (
            select(Membership)
            .where(Membership.organization_id == organization_id)
            .options(
                selectinload(Membership.user),
                selectinload(Membership.membership_roles).selectinload(
                    MembershipRole.role
                ),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def assign_role(
        self,
        organization_id: uuid.UUID,
        membership_id: uuid.UUID,
        role_id: uuid.UUID,
        assigned_by: uuid.UUID | None = None,
    ) -> MembershipRole:
        # Verify membership belongs to this organization
        mem_res = await self.session.execute(
            select(Membership).where(
                Membership.id == membership_id,
                Membership.organization_id == organization_id,
            )
        )
        if not mem_res.scalar_one_or_none():
            raise ValueError(
                "Membership does not belong to this organization or does not exist"
            )

        # Check if already assigned
        existing = await self.session.execute(
            select(MembershipRole).where(
                MembershipRole.membership_id == membership_id,
                MembershipRole.role_id == role_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Role is already assigned to this membership")

        # Verify role is valid for this organization (must be organization-scoped)
        role_res = await self.session.execute(
            select(Role).where(
                Role.id == role_id,
                Role.organization_id == organization_id,
                Role.scope == "organization",
            )
        )
        role = role_res.scalar_one_or_none()
        if not role:
            raise ValueError(
                "Role is not valid for this organization or does not exist"
            )

        membership_role = MembershipRole(
            organization_id=organization_id,
            membership_id=membership_id,
            role_id=role_id,
            assigned_by=assigned_by,
        )
        self.session.add(membership_role)
        await self.session.flush()
        return membership_role

    async def remove_role(
        self,
        organization_id: uuid.UUID,
        membership_id: uuid.UUID,
        role_id: uuid.UUID,
    ) -> bool:
        stmt = delete(MembershipRole).where(
            MembershipRole.organization_id == organization_id,
            MembershipRole.membership_id == membership_id,
            MembershipRole.role_id == role_id,
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0
