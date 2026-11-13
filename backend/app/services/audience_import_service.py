import asyncio
import csv
import hashlib
import io
import logging
import os
import tempfile
import uuid
from pathlib import Path, PurePosixPath

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.audience_import_job import AudienceImportJob
from app.models.audience_import_upload import AudienceImportUpload
from app.models.outbox_event import OutboxEvent

logger = logging.getLogger(__name__)

_ALLOWED_HEADERS = {
    "full_name",
    "email",
    "phone",
    "preferred_language",
    "district",
    "state_code",
    "city",
}
_ALLOWED_CONTENT_TYPES = {
    "application/csv",
    "application/octet-stream",
    "application/vnd.ms-excel",
    "text/csv",
    "text/x-csv",
}


def validate_audience_csv(
    *,
    filename: str | None,
    content_type: str | None,
    content: bytes,
    max_rows: int,
) -> tuple[int, str]:
    """Validate CSV structure without applying row-level audience semantics."""
    normalized_name = (filename or "").replace("\\", "/")
    if PurePosixPath(normalized_name).suffix.casefold() != ".csv":
        raise HTTPException(status_code=422, detail="Upload must be a .csv file")

    normalized_type = (content_type or "").split(";", maxsplit=1)[0].strip().lower()
    if normalized_type and normalized_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Unsupported upload media type; expected CSV",
        )

    if not content:
        raise HTTPException(status_code=422, detail="CSV file is empty")
    if b"\x00" in content:
        raise HTTPException(status_code=422, detail="CSV contains invalid characters")

    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as err:
        raise HTTPException(
            status_code=422,
            detail="CSV must use UTF-8 encoding",
        ) from err

    try:
        reader = csv.reader(io.StringIO(decoded, newline=""), strict=True)
        raw_headers = next(reader, None)
        if not raw_headers:
            raise HTTPException(status_code=422, detail="CSV header row is missing")

        headers = [header.strip().casefold() for header in raw_headers]
        if any(not header for header in headers):
            raise HTTPException(
                status_code=422,
                detail="CSV headers must not be blank",
            )
        if len(headers) != len(set(headers)):
            raise HTTPException(
                status_code=422,
                detail="CSV contains duplicate headers",
            )
        if any(header not in _ALLOWED_HEADERS for header in headers):
            raise HTTPException(
                status_code=422,
                detail="CSV contains unsupported columns",
            )
        if "full_name" not in headers:
            raise HTTPException(
                status_code=422,
                detail="CSV must include a full_name column",
            )
        if not {"email", "phone"}.intersection(headers):
            raise HTTPException(
                status_code=422,
                detail="CSV must include an email column, a phone column, or both",
            )

        row_count = 0
        for row in reader:
            if not row or all(not value.strip() for value in row):
                continue
            if len(row) != len(headers):
                raise HTTPException(
                    status_code=422,
                    detail=f"CSV row {reader.line_num} has an unexpected column count",
                )
            row_count += 1
            if row_count > max_rows:
                raise HTTPException(
                    status_code=413,
                    detail="CSV exceeds the configured row limit",
                )
    except csv.Error as err:
        raise HTTPException(
            status_code=422,
            detail="CSV structure is malformed",
        ) from err

    if row_count == 0:
        raise HTTPException(
            status_code=422,
            detail="CSV must contain at least one data row",
        )

    return row_count, hashlib.sha256(content).hexdigest()


def _store_private_csv(directory: Path, upload_id: uuid.UUID, content: bytes) -> None:
    """Persist a CSV using a generated key, private permissions, and atomic link."""
    directory = Path(directory).expanduser()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink() or not directory.is_dir():
        raise OSError("Configured audience upload path is not a private directory")
    directory.chmod(0o700)

    destination = directory / f"{upload_id.hex}.csv"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{upload_id.hex}.",
        suffix=".part",
        dir=directory,
    )
    temporary_path = Path(temporary_name)
    published = False
    try:
        with os.fdopen(descriptor, "wb") as stored_file:
            stored_file.write(content)
            stored_file.flush()
            os.fsync(stored_file.fileno())
        # A hard link publishes the completed file without overwriting an
        # existing object if an identifier collision ever occurs.
        os.link(temporary_path, destination)
        published = True
        directory_descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except Exception:
        if published:
            destination.unlink(missing_ok=True)
        raise
    finally:
        temporary_path.unlink(missing_ok=True)


def _delete_private_csv(directory: Path, upload_id: uuid.UUID) -> None:
    destination = Path(directory).expanduser() / f"{upload_id.hex}.csv"
    destination.unlink(missing_ok=True)


class AudienceImportService:
    def __init__(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        settings: Settings,
    ):
        self.session = session
        self.organization_id = organization_id
        self.actor_user_id = actor_user_id
        self.settings = settings

    async def upload_csv(
        self, upload: UploadFile
    ) -> tuple[AudienceImportUpload, AudienceImportJob]:
        try:
            content = await upload.read(self.settings.audience_import_max_bytes + 1)
        finally:
            await upload.close()

        if len(content) > self.settings.audience_import_max_bytes:
            raise HTTPException(
                status_code=413,
                detail="CSV exceeds the configured file-size limit",
            )

        row_count, checksum = validate_audience_csv(
            filename=upload.filename,
            content_type=upload.content_type,
            content=content,
            max_rows=self.settings.audience_import_max_rows,
        )
        upload_id = uuid.uuid4()
        try:
            await asyncio.to_thread(
                _store_private_csv,
                self.settings.audience_import_storage_dir,
                upload_id,
                content,
            )
        except OSError as err:
            raise HTTPException(
                status_code=503,
                detail="Audience upload storage is unavailable",
            ) from err

        job_id = uuid.uuid4()
        record = AudienceImportUpload(
            id=upload_id,
            organization_id=self.organization_id,
            uploaded_by_id=self.actor_user_id,
            byte_size=len(content),
            row_count=row_count,
            sha256=checksum,
        )
        job = AudienceImportJob(
            id=job_id,
            organization_id=self.organization_id,
            upload_id=upload_id,
            uploaded_by_id=self.actor_user_id,
            status="queued",
            total_rows=row_count,
            processed_rows=0,
            imported_rows=0,
            error_rows=0,
            chunk_size=self.settings.audience_import_chunk_size,
        )
        event = OutboxEvent(
            organization_id=self.organization_id,
            aggregate_type="audience_import_job",
            aggregate_id=job_id,
            event_type="audience_import.queued",
            payload={"job_id": str(job_id), "upload_id": str(upload_id)},
        )
        self.session.add_all([record, job, event])
        try:
            # Flush and load server-generated values before COMMIT.  The
            # PostgreSQL tenant GUC is transaction-local and is intentionally
            # cleared by commit; refreshing afterwards would run outside RLS
            # tenant context and make a successful upload appear to fail.
            await self.session.flush()
            await self.session.refresh(record)
            await self.session.refresh(job)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            try:
                await asyncio.to_thread(
                    _delete_private_csv,
                    self.settings.audience_import_storage_dir,
                    upload_id,
                )
            except OSError:
                logger.exception(
                    "Failed to remove unreferenced audience upload %s",
                    upload_id,
                )
            raise

        return record, job
