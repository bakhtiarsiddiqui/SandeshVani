import hashlib
import hmac
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth_login_attempt_window import AuthLoginAttemptWindow


class LoginAttemptRepository:
    """Database-backed failed-login throttling with atomic counter updates."""

    def __init__(self, session: AsyncSession, hmac_secret: str):
        if len(hmac_secret.encode("utf-8")) < 32:
            raise ValueError("Login throttling HMAC secret must be at least 32 bytes")
        self.session = session
        self.hmac_secret = hmac_secret.encode("utf-8")

    def key_hash(self, kind: str, value: str) -> str:
        normalized = value.strip().casefold()
        digest = hmac.new(
            self.hmac_secret,
            f"login:{kind}:{normalized}".encode("utf-8"),
            hashlib.sha256,
        )
        return digest.hexdigest()

    async def get_counts(
        self, key_hashes: list[str], window_seconds: int
    ) -> dict[str, int]:
        if not key_hashes:
            return {}
        cutoff = datetime.now(UTC) - timedelta(seconds=window_seconds)
        result = await self.session.execute(
            select(
                AuthLoginAttemptWindow.key_hash,
                AuthLoginAttemptWindow.attempt_count,
            ).where(
                AuthLoginAttemptWindow.key_hash.in_(key_hashes),
                AuthLoginAttemptWindow.window_started_at > cutoff,
            )
        )
        return {row.key_hash: row.attempt_count for row in result}

    async def record_failure(
        self, key_hashes: list[str], window_seconds: int
    ) -> None:
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=window_seconds)
        dialect = self.session.bind.dialect.name
        insert = (
            pg_insert
            if dialect == "postgresql"
            else sqlite_insert
            if dialect == "sqlite"
            else None
        )
        if insert is None:
            raise RuntimeError(
                f"Login throttling is not implemented for database dialect {dialect}"
            )

        model = AuthLoginAttemptWindow
        expired = model.window_started_at <= cutoff
        for key_hash in dict.fromkeys(key_hashes):
            statement = (
                insert(model)
                .values(
                    key_hash=key_hash,
                    attempt_count=1,
                    window_started_at=now,
                    updated_at=now,
                )
                .on_conflict_do_update(
                    index_elements=[model.key_hash],
                    set_={
                        "attempt_count": case(
                            (expired, 1), else_=model.attempt_count + 1
                        ),
                        "window_started_at": case(
                            (expired, now), else_=model.window_started_at
                        ),
                        "updated_at": now,
                    },
                )
            )
            await self.session.execute(statement)

        await self.session.execute(
            delete(model).where(
                model.window_started_at < now - timedelta(days=1)
            )
        )
        await self.session.flush()

    async def clear(self, key_hashes: list[str]) -> None:
        if not key_hashes:
            return
        await self.session.execute(
            delete(AuthLoginAttemptWindow).where(
                AuthLoginAttemptWindow.key_hash.in_(key_hashes)
            )
        )
        await self.session.flush()
