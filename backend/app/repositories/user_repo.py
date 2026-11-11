import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_normalized_email(self, normalized_email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.normalized_email == normalized_email)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str,
        normalized_email: str,
        password_hash: str,
        full_name: str,
        status: str = "pending_verification",
    ) -> User:
        user = User(
            email=email,
            normalized_email=normalized_email,
            password_hash=password_hash,
            full_name=full_name,
            status=status,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def mark_email_verified(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                status="active",
                email_verified_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.flush()

    async def update_password(self, user_id: uuid.UUID, new_password_hash: str) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                password_hash=new_password_hash,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.flush()
