import uuid

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.http_status import HTTP_422_UNPROCESSABLE_CONTENT
from app.models.audience_member import AudienceMember
from app.repositories.audience_repo import AudienceRepository
from app.schemas.audience import AudienceMemberCreate


class AudienceService:
    def __init__(self, session: AsyncSession, organization_id: uuid.UUID):
        self.repository = AudienceRepository(session, organization_id)

    async def list_members(self, **filters):
        try:
            return await self.repository.list(**filters)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            ) from err

    async def get_member(self, member_id: uuid.UUID) -> AudienceMember:
        member = await self.repository.get_by_id(member_id)
        if member is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audience member not found",
            )
        return member

    async def create_member(
        self, values: dict, actor_user_id: uuid.UUID
    ) -> AudienceMember:
        return await self.repository.create(
            values=values,
            actor_user_id=actor_user_id,
        )

    async def update_member(
        self,
        member_id: uuid.UUID,
        values: dict,
        actor_user_id: uuid.UUID,
    ) -> AudienceMember:
        member = await self.get_member(member_id)
        merged = {
            "full_name": member.full_name,
            "email": member.email,
            "phone": member.phone,
            "preferred_language": member.preferred_language,
            "district": member.district,
        }
        merged.update({key: value for key, value in values.items() if key != "status"})

        try:
            AudienceMemberCreate.model_validate(merged)
        except ValidationError as err:
            # Do not echo email addresses or phone numbers in the public error.
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Update must leave at least one valid contact point",
            ) from err

        return await self.repository.update(
            member,
            values=values,
            actor_user_id=actor_user_id,
        )
