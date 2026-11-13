import uuid

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.http_status import HTTP_422_UNPROCESSABLE_CONTENT
from app.models.audience_member import AudienceMember
from app.repositories.audience_repo import AudienceRepository
from app.schemas.audience import AudienceMemberCreate
from app.services.audience_identity import is_identity_unique_violation


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

    async def _ensure_identity_available(
        self,
        *,
        email: str | None,
        phone: str | None,
        exclude_member_id: uuid.UUID | None = None,
    ) -> None:
        matches = await self.repository.find_identity_matches(
            email=email,
            phone=phone,
            exclude_member_id=exclude_member_id,
        )
        if matches:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "An audience contact with one or more supplied "
                    "identifiers already exists"
                ),
            )

    async def _raise_concurrent_identity_conflict(
        self,
        error: IntegrityError,
        *,
        email: str | None,
        phone: str | None,
        exclude_member_id: uuid.UUID | None = None,
    ) -> None:
        if not is_identity_unique_violation(error):
            raise error
        matches = await self.repository.find_identity_matches(
            email=email,
            phone=phone,
            exclude_member_id=exclude_member_id,
        )
        if not matches:
            raise error
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "An audience contact with one or more supplied "
                "identifiers already exists"
            ),
        ) from error

    async def create_member(
        self, values: dict, actor_user_id: uuid.UUID
    ) -> AudienceMember:
        await self._ensure_identity_available(
            email=values.get("email"),
            phone=values.get("phone"),
        )
        try:
            return await self.repository.create(
                values=values,
                actor_user_id=actor_user_id,
            )
        except IntegrityError as err:
            await self._raise_concurrent_identity_conflict(
                err,
                email=values.get("email"),
                phone=values.get("phone"),
            )
            raise

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

        await self._ensure_identity_available(
            email=merged.get("email"),
            phone=merged.get("phone"),
            exclude_member_id=member_id,
        )
        try:
            return await self.repository.update(
                member,
                values=values,
                actor_user_id=actor_user_id,
            )
        except IntegrityError as err:
            await self._raise_concurrent_identity_conflict(
                err,
                email=merged.get("email"),
                phone=merged.get("phone"),
                exclude_member_id=member_id,
            )
            raise
