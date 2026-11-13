import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.membership import Membership
from app.models.organization import Organization


class OrganizationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, organization_id: uuid.UUID) -> Organization | None:
        result = await self.session.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        return result.scalar_one_or_none()

    async def lock_for_update(self, organization_id: uuid.UUID) -> Organization | None:
        result = await self.session.execute(
            select(Organization)
            .where(Organization.id == organization_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Organization | None:
        result = await self.session.execute(
            select(Organization).where(Organization.slug == slug)
        )
        return result.scalar_one_or_none()

    async def create(
        self, name: str, slug: str, status: str = "active"
    ) -> Organization:
        organization = Organization(name=name, slug=slug, status=status)
        self.session.add(organization)
        await self.session.flush()
        return organization

    async def get_user_organizations(self, user_id: uuid.UUID) -> list[Organization]:
        stmt = (
            select(Organization)
            .join(Membership, Membership.organization_id == Organization.id)
            .where(
                Membership.user_id == user_id,
                Membership.status == "active",
                Organization.status == "active",
            )
            .order_by(Organization.created_at.asc(), Organization.id.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
