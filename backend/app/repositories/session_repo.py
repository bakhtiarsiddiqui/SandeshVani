import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth_session import AuthSession
from app.models.token import (
    EmailVerificationToken,
    PasswordResetToken,
    RefreshToken,
)


class SessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # AuthSession
    async def create_session(
        self,
        user_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
        expires_days: int = 7,
    ) -> AuthSession:
        now = datetime.now(UTC)
        auth_session = AuthSession(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now,
            expires_at=now + timedelta(days=expires_days),
        )
        self.session.add(auth_session)
        await self.session.flush()
        return auth_session

    async def get_session(self, session_id: uuid.UUID) -> AuthSession | None:
        result = await self.session.execute(
            select(AuthSession).where(AuthSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def revoke_session(self, session_id: uuid.UUID) -> None:
        await self.session.execute(
            update(AuthSession)
            .where(AuthSession.id == session_id)
            .values(revoked_at=datetime.now(UTC))
        )
        await self.session.flush()

    async def revoke_all_user_sessions(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            update(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        await self.session.flush()

    # RefreshToken
    async def create_refresh_token(
        self,
        session_id: uuid.UUID,
        token_hash: str,
        family_id: uuid.UUID,
        expires_days: int = 7,
    ) -> RefreshToken:
        now = datetime.now(UTC)
        refresh_token = RefreshToken(
            session_id=session_id,
            token_hash=token_hash,
            family_id=family_id,
            is_revoked=False,
            created_at=now,
            expires_at=now + timedelta(days=expires_days),
        )
        self.session.add(refresh_token)
        await self.session.flush()
        return refresh_token

    async def get_refresh_token_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def consume_active_refresh_token(self, token_id: uuid.UUID) -> bool:
        """Atomically consume a token exactly once across database workers.

        Uses ``synchronize_session=False`` because:
        1. The row will never be reused in this request — rotation issues a
           replacement immediately afterwards.
        2. SQLAlchemy's in-Python evaluator crashes on SQLite when comparing
           offset-naive ``expires_at`` against offset-aware ``now(UTC)``.  The
           database-side comparison is the authoritative check.
        """
        now = datetime.now(UTC)
        result = await self.session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.id == token_id,
                RefreshToken.rotated_at.is_(None),
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
            .values(rotated_at=now)
            .execution_options(synchronize_session=False)
        )
        await self.session.flush()
        return result.rowcount == 1

    async def link_refresh_replacement(
        self, token_id: uuid.UUID, replacement_id: uuid.UUID
    ) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(replaced_by_id=replacement_id)
        )
        await self.session.flush()

    async def revoke_refresh_token(self, token_id: uuid.UUID) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(is_revoked=True, revoked_at=datetime.now(UTC))
        )
        await self.session.flush()

    async def revoke_family_tokens(self, family_id: uuid.UUID) -> None:
        """Revoke all tokens in a family (triggered upon reuse detection)."""
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id)
            .values(is_revoked=True, revoked_at=datetime.now(UTC))
        )
        await self.session.flush()

    # EmailVerificationToken
    async def create_email_token(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_hours: int = 24,
    ) -> EmailVerificationToken:
        now = datetime.now(UTC)
        token = EmailVerificationToken(
            user_id=user_id,
            token_hash=token_hash,
            created_at=now,
            expires_at=now + timedelta(hours=expires_hours),
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_email_token_by_hash(
        self, token_hash: str
    ) -> EmailVerificationToken | None:
        result = await self.session.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == token_hash
            )
        )
        return result.scalar_one_or_none()

    async def mark_email_token_used(self, token_id: uuid.UUID) -> None:
        await self.session.execute(
            update(EmailVerificationToken)
            .where(EmailVerificationToken.id == token_id)
            .values(used_at=datetime.now(UTC))
        )
        await self.session.flush()

    # PasswordResetToken
    async def create_password_reset_token(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_hours: int = 1,
    ) -> PasswordResetToken:
        now = datetime.now(UTC)
        token = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            created_at=now,
            expires_at=now + timedelta(hours=expires_hours),
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_password_reset_token_by_hash(
        self, token_hash: str
    ) -> PasswordResetToken | None:
        result = await self.session.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash
            )
        )
        return result.scalar_one_or_none()

    async def mark_password_reset_token_used(self, token_id: uuid.UUID) -> None:
        await self.session.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.id == token_id)
            .values(used_at=datetime.now(UTC))
        )
        await self.session.flush()
