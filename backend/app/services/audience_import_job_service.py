import base64
import binascii
import json
import uuid

from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.http_status import HTTP_422_UNPROCESSABLE_CONTENT
from app.models.audience_import_job import AudienceImportJob
from app.models.audience_import_job_error import AudienceImportJobError


def _encode_error_cursor(error: AudienceImportJobError) -> str:
    payload = json.dumps(
        {"row_number": error.row_number, "id": str(error.id)},
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_error_cursor(cursor: str) -> tuple[int, uuid.UUID]:
    if not cursor or len(cursor) > 512:
        raise ValueError("Invalid import error cursor")
    try:
        padded = cursor + ("=" * (-len(cursor) % 4))
        payload = json.loads(
            base64.b64decode(
                padded.encode("ascii"),
                altchars=b"-_",
                validate=True,
            )
        )
        if not isinstance(payload, dict) or set(payload) != {"row_number", "id"}:
            raise ValueError("Invalid import error cursor")
        row_number = payload["row_number"]
        if not isinstance(row_number, int) or row_number < 2:
            raise ValueError("Invalid import error cursor")
        return row_number, uuid.UUID(payload["id"])
    except (
        ValueError,
        TypeError,
        KeyError,
        UnicodeDecodeError,
        UnicodeEncodeError,
        AttributeError,
        json.JSONDecodeError,
        binascii.Error,
    ) as err:
        raise ValueError("Invalid import error cursor") from err


class AudienceImportJobService:
    def __init__(self, session: AsyncSession, organization_id: uuid.UUID):
        if not organization_id:
            raise ValueError("AudienceImportJobService requires a verified tenant")
        self.session = session
        self.organization_id = organization_id

    async def get_job(self, job_id: uuid.UUID) -> AudienceImportJob:
        result = await self.session.execute(
            select(AudienceImportJob).where(
                AudienceImportJob.organization_id == self.organization_id,
                AudienceImportJob.id == job_id,
            )
        )
        job = result.scalar_one_or_none()
        if job is None:
            raise HTTPException(status_code=404, detail="Audience import not found")
        return job

    async def list_errors(
        self,
        *,
        job_id: uuid.UUID,
        limit: int,
        cursor: str | None = None,
    ) -> tuple[list[AudienceImportJobError], bool, str | None]:
        await self.get_job(job_id)
        stmt = select(AudienceImportJobError).where(
            AudienceImportJobError.organization_id == self.organization_id,
            AudienceImportJobError.import_job_id == job_id,
        )
        if cursor:
            try:
                row_number, error_id = _decode_error_cursor(cursor)
            except ValueError as err:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Invalid import error cursor",
                ) from err
            stmt = stmt.where(
                or_(
                    AudienceImportJobError.row_number > row_number,
                    and_(
                        AudienceImportJobError.row_number == row_number,
                        AudienceImportJobError.id > error_id,
                    ),
                )
            )

        stmt = stmt.order_by(
            AudienceImportJobError.row_number.asc(),
            AudienceImportJobError.id.asc(),
        ).limit(limit + 1)
        result = await self.session.execute(stmt)
        errors = list(result.scalars().all())
        has_more = len(errors) > limit
        if has_more:
            errors = errors[:limit]
        next_cursor = _encode_error_cursor(errors[-1]) if has_more and errors else None
        return errors, has_more, next_cursor
