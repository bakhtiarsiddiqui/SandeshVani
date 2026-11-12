import asyncio
import csv
import hashlib
import logging
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote

import asyncpg
from celery import Task
from pydantic import ValidationError
from sqlalchemy import or_, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings, get_settings
from app.db.session import set_tenant_context
from app.models.audience_import_job import AudienceImportJob
from app.models.audience_import_job_error import AudienceImportJobError
from app.models.audience_import_upload import AudienceImportUpload
from app.models.audience_member import AudienceMember
from app.models.organization import Organization
from app.models.outbox_event import OutboxEvent
from app.schemas.audience import AudienceMemberCreate
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

_IMPORT_EVENT_TYPE = "audience_import.requested"
_ALLOWED_HEADERS = {
    "full_name",
    "email",
    "phone",
    "preferred_language",
    "district",
}
_TERMINAL_JOB_STATUSES = {"completed", "completed_with_errors", "failed"}


class ImportSourceError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _advisory_lock_key(job_id: uuid.UUID) -> int:
    return int.from_bytes(job_id.bytes[:8], byteorder="big", signed=True)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _row_validation_errors(
    *,
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
    row_number: int,
    error: ValidationError,
) -> list[AudienceImportJobError]:
    errors: list[AudienceImportJobError] = []
    seen: set[tuple[str | None, str]] = set()
    for item in error.errors():
        location = item.get("loc") or ()
        candidate = str(location[0]) if location else None
        field_name = candidate if candidate in _ALLOWED_HEADERS else None
        if candidate == "email":
            error_code = "invalid_email"
        elif candidate == "phone":
            error_code = "invalid_phone"
        elif candidate == "preferred_language":
            error_code = "unsupported_language"
        elif candidate == "full_name":
            error_code = "invalid_full_name"
        elif candidate == "district":
            error_code = "invalid_district"
        elif not location:
            error_code = "missing_contact"
        elif item.get("type") == "missing":
            error_code = "required_field"
        else:
            error_code = "invalid_value"

        key = (field_name, error_code)
        if key in seen:
            continue
        seen.add(key)
        errors.append(
            AudienceImportJobError(
                organization_id=organization_id,
                import_job_id=job_id,
                row_number=row_number,
                field_name=field_name,
                error_code=error_code,
            )
        )

    if not errors:
        errors.append(
            AudienceImportJobError(
                organization_id=organization_id,
                import_job_id=job_id,
                row_number=row_number,
                field_name=None,
                error_code="invalid_row",
            )
        )
    return errors


def _prepare_row(
    *,
    raw_row: dict[str | None, Any],
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
    row_number: int,
) -> tuple[dict | None, list[AudienceImportJobError]]:
    if None in raw_row or any(value is None for value in raw_row.values()):
        return None, [
            AudienceImportJobError(
                organization_id=organization_id,
                import_job_id=job_id,
                row_number=row_number,
                field_name=None,
                error_code="invalid_column_count",
            )
        ]

    values = {
        str(key).strip().casefold(): (value or "").strip()
        for key, value in raw_row.items()
        if key is not None
    }
    for field_name in ("email", "phone", "district"):
        if values.get(field_name) == "":
            values[field_name] = None
    if values.get("preferred_language") == "":
        values["preferred_language"] = "en"

    try:
        validated = AudienceMemberCreate.model_validate(values)
    except ValidationError as err:
        return None, _row_validation_errors(
            organization_id=organization_id,
            job_id=job_id,
            row_number=row_number,
            error=err,
        )
    return validated.model_dump(), []


async def _mark_job_failed_in_transaction(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    job: AudienceImportJob,
    failure_code: str,
) -> None:
    now = datetime.now(UTC)
    job.status = "failed"
    job.failure_code = failure_code
    job.completed_at = now
    event = await session.scalar(
        select(OutboxEvent).where(
            OutboxEvent.organization_id == organization_id,
            OutboxEvent.aggregate_type == "audience_import_job",
            OutboxEvent.aggregate_id == job.id,
            OutboxEvent.event_type == _IMPORT_EVENT_TYPE,
        )
    )
    if event is not None:
        event.status = "failed"
        event.completed_at = now
        event.last_error_code = failure_code


async def _mark_import_failed(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
    failure_code: str,
) -> None:
    async with session.begin():
        await set_tenant_context(session, organization_id)
        job = await session.scalar(
            select(AudienceImportJob)
            .where(
                AudienceImportJob.organization_id == organization_id,
                AudienceImportJob.id == job_id,
            )
            .with_for_update()
        )
        if job is None or job.status in _TERMINAL_JOB_STATUSES:
            return
        await _mark_job_failed_in_transaction(
            session,
            organization_id=organization_id,
            job=job,
            failure_code=failure_code,
        )


async def _persist_chunk(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
    expected_processed_rows: int,
    chunk: list[tuple[int, dict[str | None, Any]]],
) -> bool:
    async with session.begin():
        await set_tenant_context(session, organization_id)
        job = await session.scalar(
            select(AudienceImportJob)
            .where(
                AudienceImportJob.organization_id == organization_id,
                AudienceImportJob.id == job_id,
            )
            .with_for_update()
        )
        if job is None or job.status != "processing":
            return False
        if job.processed_rows != expected_processed_rows:
            return False
        if job.processed_rows + len(chunk) > job.total_rows:
            raise ImportSourceError("source_row_count_mismatch")

        members: list[AudienceMember] = []
        errors: list[AudienceImportJobError] = []
        rejected_rows = 0
        for row_number, raw_row in chunk:
            values, row_errors = _prepare_row(
                raw_row=raw_row,
                organization_id=organization_id,
                job_id=job_id,
                row_number=row_number,
            )
            if row_errors:
                rejected_rows += 1
                errors.extend(row_errors)
                continue
            members.append(
                AudienceMember(
                    organization_id=organization_id,
                    created_by=job.created_by_id,
                    updated_by=job.created_by_id,
                    **values,
                )
            )

        session.add_all(members)
        session.add_all(errors)
        job.processed_rows += len(chunk)
        job.imported_rows += len(members)
        job.rejected_rows += rejected_rows
    return True


async def process_import_job_in_session(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
    settings: Settings,
) -> None:
    """Process bounded CSV chunks; each committed chunk can be safely resumed."""
    async with session.begin():
        await set_tenant_context(session, organization_id)
        job = await session.scalar(
            select(AudienceImportJob)
            .where(
                AudienceImportJob.organization_id == organization_id,
                AudienceImportJob.id == job_id,
            )
            .with_for_update()
        )
        if job is None or job.status in _TERMINAL_JOB_STATUSES:
            return
        upload = await session.scalar(
            select(AudienceImportUpload).where(
                AudienceImportUpload.organization_id == organization_id,
                AudienceImportUpload.id == job.upload_id,
            )
        )
        if upload is None:
            await _mark_job_failed_in_transaction(
                session,
                organization_id=organization_id,
                job=job,
                failure_code="upload_metadata_missing",
            )
            return
        job.status = "processing"
        if job.started_at is None:
            job.started_at = datetime.now(UTC)
        upload_id = upload.id
        expected_sha256 = upload.sha256
        total_rows = job.total_rows
        processed_rows = job.processed_rows

    file_path = Path(settings.audience_import_storage_dir).expanduser() / (
        f"{upload_id.hex}.csv"
    )
    try:
        if file_path.is_symlink() or not file_path.is_file():
            raise ImportSourceError("source_file_missing")
        if _sha256_file(file_path) != expected_sha256:
            raise ImportSourceError("source_checksum_mismatch")

        with file_path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source, strict=True)
            raw_headers = reader.fieldnames or []
            headers = [header.strip().casefold() for header in raw_headers]
            if (
                not headers
                or any(not header for header in headers)
                or len(headers) != len(set(headers))
                or any(header not in _ALLOWED_HEADERS for header in headers)
                or "full_name" not in headers
                or not {"email", "phone"}.intersection(headers)
            ):
                raise ImportSourceError("source_headers_invalid")

            seen_nonblank_rows = 0
            chunk: list[tuple[int, dict[str | None, Any]]] = []
            for raw_row in reader:
                raw_values = list(raw_row.values())
                if all(
                    value is None or (isinstance(value, str) and not value.strip())
                    for value in raw_values
                ):
                    continue
                seen_nonblank_rows += 1
                if seen_nonblank_rows <= processed_rows:
                    continue
                chunk.append((reader.line_num, raw_row))
                if len(chunk) >= settings.audience_import_chunk_size:
                    persisted = await _persist_chunk(
                        session,
                        organization_id=organization_id,
                        job_id=job_id,
                        expected_processed_rows=processed_rows,
                        chunk=chunk,
                    )
                    if not persisted:
                        raise ImportSourceError("job_state_changed")
                    processed_rows += len(chunk)
                    chunk = []

            if chunk:
                persisted = await _persist_chunk(
                    session,
                    organization_id=organization_id,
                    job_id=job_id,
                    expected_processed_rows=processed_rows,
                    chunk=chunk,
                )
                if not persisted:
                    raise ImportSourceError("job_state_changed")
                processed_rows += len(chunk)

        if seen_nonblank_rows != total_rows:
            raise ImportSourceError("source_row_count_mismatch")
    except ImportSourceError as err:
        await _mark_import_failed(
            session,
            organization_id=organization_id,
            job_id=job_id,
            failure_code=err.code,
        )
        return
    except (csv.Error, UnicodeDecodeError):
        await _mark_import_failed(
            session,
            organization_id=organization_id,
            job_id=job_id,
            failure_code="source_csv_invalid",
        )
        return
    except OSError:
        await _mark_import_failed(
            session,
            organization_id=organization_id,
            job_id=job_id,
            failure_code="source_file_unavailable",
        )
        return

    async with session.begin():
        await set_tenant_context(session, organization_id)
        job = await session.scalar(
            select(AudienceImportJob)
            .where(
                AudienceImportJob.organization_id == organization_id,
                AudienceImportJob.id == job_id,
            )
            .with_for_update()
        )
        if job is None or job.status in _TERMINAL_JOB_STATUSES:
            return
        if job.processed_rows != job.total_rows:
            await _mark_job_failed_in_transaction(
                session,
                organization_id=organization_id,
                job=job,
                failure_code="processed_row_count_mismatch",
            )
            return
        now = datetime.now(UTC)
        job.status = "completed_with_errors" if job.rejected_rows else "completed"
        job.completed_at = now
        event = await session.scalar(
            select(OutboxEvent).where(
                OutboxEvent.organization_id == organization_id,
                OutboxEvent.aggregate_type == "audience_import_job",
                OutboxEvent.aggregate_id == job_id,
                OutboxEvent.event_type == _IMPORT_EVENT_TYPE,
            )
        )
        if event is not None:
            event.status = "completed"
            event.completed_at = now
            event.last_error_code = None


async def _execute_import_task(
    *,
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
    settings: Settings,
) -> None:
    # Hold a dedicated PostgreSQL session-level advisory lock across commits.
    # A separate asyncpg connection avoids releasing the lock when SQLAlchemy
    # returns a NullPool connection after a transaction.
    db_url = make_url(settings.get_database_url()).set(drivername="postgresql")
    lock_connection = await asyncpg.connect(
        db_url.render_as_string(hide_password=False)
    )
    lock_key = _advisory_lock_key(job_id)
    lock_acquired = False
    engine = None
    try:
        lock_acquired = bool(
            await lock_connection.fetchval(
                "SELECT pg_try_advisory_lock($1)",
                lock_key,
            )
        )
        if not lock_acquired:
            return

        engine = create_async_engine(
            settings.get_database_url(),
            poolclass=NullPool,
            pool_pre_ping=True,
        )
        factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        async with factory() as session:
            await process_import_job_in_session(
                session,
                organization_id=organization_id,
                job_id=job_id,
                settings=settings,
            )
    finally:
        if lock_acquired:
            await lock_connection.execute(
                "SELECT pg_advisory_unlock($1)",
                lock_key,
            )
        await lock_connection.close()
        if engine is not None:
            await engine.dispose()


async def _mark_task_failed(
    *,
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
    settings: Settings,
) -> None:
    engine = create_async_engine(
        settings.get_database_url(),
        poolclass=NullPool,
        pool_pre_ping=True,
    )
    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    try:
        async with factory() as session:
            await _mark_import_failed(
                session,
                organization_id=organization_id,
                job_id=job_id,
                failure_code="worker_retries_exhausted",
            )
    finally:
        await engine.dispose()


async def _publish_outbox_events(settings: Settings) -> int:
    engine = create_async_engine(
        settings.get_database_url(),
        poolclass=NullPool,
        pool_pre_ping=True,
    )
    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    dispatched = 0
    try:
        async with factory() as session:
            organization_ids = list(
                (
                    await session.scalars(
                        select(Organization.id).order_by(Organization.id)
                    )
                ).all()
            )
            await session.commit()
            for organization_id in organization_ids:
                async with session.begin():
                    await set_tenant_context(session, organization_id)
                    now = datetime.now(UTC)
                    events = list(
                        (
                            await session.scalars(
                                select(OutboxEvent)
                                .where(
                                    OutboxEvent.organization_id == organization_id,
                                    OutboxEvent.event_type == _IMPORT_EVENT_TYPE,
                                    OutboxEvent.status.in_(("pending", "dispatched")),
                                    OutboxEvent.available_at <= now,
                                )
                                .order_by(OutboxEvent.created_at.asc())
                                .limit(50)
                                .with_for_update(skip_locked=True)
                            )
                        ).all()
                    )
                    for event in events:
                        try:
                            process_audience_import.apply_async(
                                args=[
                                    str(organization_id),
                                    str(event.payload["job_id"]),
                                ],
                                queue="audience-imports",
                            )
                        except Exception:
                            event.dispatch_attempts += 1
                            delay = min(
                                300,
                                5 * (2 ** min(event.dispatch_attempts, 6)),
                            )
                            event.status = "pending"
                            event.available_at = now + timedelta(seconds=delay)
                            event.last_error_code = "broker_unavailable"
                            logger.warning(
                                "Audience import outbox dispatch failed for event %s",
                                event.id,
                            )
                        else:
                            event.dispatch_attempts += 1
                            event.status = "dispatched"
                            event.last_dispatched_at = now
                            event.available_at = now + timedelta(seconds=60)
                            event.last_error_code = None
                            dispatched += 1
        return dispatched
    finally:
        await engine.dispose()


@celery_app.task(
    bind=True,
    name="app.workers.audience_imports.process_audience_import",
    max_retries=5,
    acks_late=True,
)
def process_audience_import(
    self: Task,
    organization_id: str,
    job_id: str,
) -> None:
    settings = get_settings()
    tenant_id = uuid.UUID(organization_id)
    import_id = uuid.UUID(job_id)
    try:
        asyncio.run(
            _execute_import_task(
                organization_id=tenant_id,
                job_id=import_id,
                settings=settings,
            )
        )
    except Exception as err:
        if self.request.retries >= self.max_retries:
            asyncio.run(
                _mark_task_failed(
                    organization_id=tenant_id,
                    job_id=import_id,
                    settings=settings,
                )
            )
            raise
        countdown = min(300, 5 * (2**self.request.retries))
        raise self.retry(exc=err, countdown=countdown) from err


@celery_app.task(
    name="app.workers.audience_imports.publish_pending_audience_imports",
)
def publish_pending_audience_imports() -> int:
    return asyncio.run(_publish_outbox_events(get_settings()))
