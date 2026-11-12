import base64
import binascii
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audience_member import AudienceMember


def encode_cursor(member: AudienceMember) -> str:
    created_at = member.created_at
    if created_at.tzinfo is None:
        # SQLite drops timezone metadata for DateTime(timezone=True); application
        # timestamps are UTC, so restore UTC before serializing the test cursor.
        created_at = created_at.replace(tzinfo=UTC)
    payload = json.dumps(
        {"created_at": created_at.isoformat(), "id": str(member.id)},
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    if not cursor or len(cursor) > 512:
        raise ValueError("Invalid audience cursor")
    try:
        padded = cursor + ("=" * (-len(cursor) % 4))
        payload = json.loads(
            base64.b64decode(padded.encode("ascii"), altchars=b"-_", validate=True)
        )
        if not isinstance(payload, dict) or set(payload) != {"created_at", "id"}:
            raise ValueError("Invalid audience cursor")
        created_at = datetime.fromisoformat(payload["created_at"])
        if created_at.tzinfo is None:
            raise ValueError("Invalid audience cursor")
        member_id = uuid.UUID(payload["id"])
    except (
        ValueError,
        TypeError,
        KeyError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        binascii.Error,
    ) as err:
        raise ValueError("Invalid audience cursor") from err
    return created_at, member_id


class AudienceRepository:
    def __init__(self, session: AsyncSession, organization_id: uuid.UUID):
        if not organization_id:
            raise ValueError("AudienceRepository requires a verified organization_id")
        self.session = session
        self.organization_id = organization_id

    async def create(self, *, values: dict, actor_user_id: uuid.UUID) -> AudienceMember:
        member = AudienceMember(
            organization_id=self.organization_id,
            created_by=actor_user_id,
            updated_by=actor_user_id,
            **values,
        )
        self.session.add(member)
        await self.session.flush()
        return member

    async def get_by_id(self, member_id: uuid.UUID) -> AudienceMember | None:
        result = await self.session.execute(
            select(AudienceMember).where(
                AudienceMember.organization_id == self.organization_id,
                AudienceMember.id == member_id,
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        limit: int,
        cursor: str | None = None,
        search: str | None = None,
        status: str | None = None,
        district: str | None = None,
        language: str | None = None,
    ) -> tuple[list[AudienceMember], bool, str | None]:
        stmt = select(AudienceMember).where(
            AudienceMember.organization_id == self.organization_id
        )

        if search:
            escaped = (
                search.strip()
                .lower()
                .replace("!", "!!")
                .replace("%", "!%")
                .replace("_", "!_")
            )
            pattern = f"%{escaped}%"
            stmt = stmt.where(
                or_(
                    func.lower(AudienceMember.full_name).like(pattern, escape="!"),
                    func.lower(AudienceMember.email).like(pattern, escape="!"),
                    func.lower(AudienceMember.phone).like(pattern, escape="!"),
                )
            )

        if status:
            stmt = stmt.where(AudienceMember.status == status)
        if district:
            stmt = stmt.where(
                func.lower(AudienceMember.district) == district.strip().lower()
            )
        if language:
            stmt = stmt.where(AudienceMember.preferred_language == language)

        if cursor:
            created_at, member_id = decode_cursor(cursor)
            stmt = stmt.where(
                or_(
                    AudienceMember.created_at < created_at,
                    and_(
                        AudienceMember.created_at == created_at,
                        AudienceMember.id < member_id,
                    ),
                )
            )

        stmt = stmt.order_by(
            AudienceMember.created_at.desc(), AudienceMember.id.desc()
        ).limit(limit + 1)
        result = await self.session.execute(stmt)
        members = list(result.scalars().all())
        has_more = len(members) > limit
        if has_more:
            members = members[:limit]
        next_cursor = encode_cursor(members[-1]) if has_more and members else None
        return members, has_more, next_cursor

    async def update(
        self,
        member: AudienceMember,
        *,
        values: dict,
        actor_user_id: uuid.UUID,
    ) -> AudienceMember:
        for field_name, value in values.items():
            setattr(member, field_name, value)
        member.updated_by = actor_user_id
        await self.session.flush()
        return member
