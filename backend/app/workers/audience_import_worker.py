import csv
import hashlib
import logging
import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.audience_import_job import AudienceImportJob
from app.models.audience_import_job_error import AudienceImportJobError
from app.models.audience_import_upload import AudienceImportUpload
from app.models.audience_member import AudienceMember
from app.schemas.audience import AudienceMemberCreate
from app.services.audience_identity import (
    classify_identity_match,
    is_identity_unique_violation,
)

logger = logging.getLogger(__name__)

_TERMINAL_STATUSES = {"completed", "completed_with_errors", "failed"}
_ALLOWED_HEADERS = {
    "full_name",
    "email",
    "phone",
    "preferred_language",
    "district",
}


class UploadProcessingError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _set_tenant_context(session: Session, organization_id: uuid.UUID) -> None:
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        session.execute(
            text("SELECT set_config('app.current_org', :org_id, true)"),
            {"org_id": str(organization_id)},
        )


def _iter_nonblank_rows(
    reader: csv.reader,
) -> Iterator[tuple[int, list[str]]]:
    logical_row_number = 1
    for row in reader:
        if not row or all(not value.strip() for value in row):
            continue
        logical_row_number += 1
        yield logical_row_number, row


def _safe_validation_errors(error: ValidationError) -> list[dict[str, str | None]]:
    """Return allowlisted issue metadata; never persist rejected cell values."""
    safe_errors: list[dict[str, str | None]] = []
    seen: set[tuple[str | None, str]] = set()

    for issue in error.errors(include_url=False):
        location = issue.get("loc", ())
        field = str(location[0]) if location else None

        if not location:
            field = None
            code = "CONTACT_POINT_REQUIRED"
        elif field == "full_name":
            code = "INVALID_FULL_NAME"
        elif field == "email":
            code = "INVALID_EMAIL"
        elif field == "phone":
            code = "INVALID_PHONE"
        elif field == "preferred_language":
            code = "UNSUPPORTED_LANGUAGE"
        elif field == "district":
            code = "INVALID_DISTRICT"
        else:
            field = None
            code = "INVALID_ROW"

        issue_key = (field, code)
        if issue_key in seen:
            continue
        seen.add(issue_key)
        safe_errors.append({"field_name": field, "error_code": code})

    return safe_errors or [{"field_name": None, "error_code": "INVALID_ROW"}]


def _validate_contact_row(row: dict[str, str | None]) -> dict | list[dict]:
    values = {
        "full_name": row.get("full_name") or "",
        "email": (row.get("email") or "").strip() or None,
        "phone": (row.get("phone") or "").strip() or None,
        "preferred_language": (row.get("preferred_language") or "").strip() or "en",
        "district": (row.get("district") or "").strip() or None,
    }
    try:
        return AudienceMemberCreate.model_validate(values).model_dump()
    except ValidationError as error:
        return _safe_validation_errors(error)


def _find_duplicate_issue(
    session: Session,
    organization_id: uuid.UUID,
    contact: dict,
) -> dict[str, str | None] | None:
    filters = []
    email = contact.get("email")
    phone = contact.get("phone")
    if email:
        filters.append(
            func.lower(func.trim(AudienceMember.email)) == email.strip().lower()
        )
    if phone:
        filters.append(func.trim(AudienceMember.phone) == phone.strip())
    if not filters:
        return None

    matches = list(
        session.scalars(
            select(AudienceMember)
            .where(
                AudienceMember.organization_id == organization_id,
                or_(*filters),
            )
            .order_by(AudienceMember.id.asc())
        ).all()
    )
    return classify_identity_match(matches, email=email, phone=phone)


def _file_digest(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


class AudienceImportWorker:
    """Resumable worker that commits one bounded CSV chunk per transaction."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        storage_dir: Path,
        lease_seconds: int = 120,
    ):
        self.session_factory = session_factory
        self.storage_dir = Path(storage_dir)
        self.lease_seconds = lease_seconds

    def _claim(
        self,
        job_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> dict | None:
        now = datetime.now(UTC)
        with self.session_factory.begin() as session:
            _set_tenant_context(session, organization_id)
            job = session.scalar(
                select(AudienceImportJob)
                .where(
                    AudienceImportJob.organization_id == organization_id,
                    AudienceImportJob.id == job_id,
                )
                .with_for_update()
            )
            if job is None or job.status in _TERMINAL_STATUSES:
                return None
            lease_expires_at = job.lease_expires_at
            if lease_expires_at is not None and lease_expires_at.tzinfo is None:
                lease_expires_at = lease_expires_at.replace(tzinfo=UTC)
            if (
                job.status == "processing"
                and lease_expires_at is not None
                and lease_expires_at > now
            ):
                return None

            upload = session.scalar(
                select(AudienceImportUpload).where(
                    AudienceImportUpload.organization_id == organization_id,
                    AudienceImportUpload.id == job.upload_id,
                )
            )
            if upload is None:
                job.status = "failed"
                job.last_error_code = "UPLOAD_METADATA_MISSING"
                job.completed_at = now
                job.worker_token = None
                job.lease_expires_at = None
                return None

            token = uuid.uuid4()
            job.status = "processing"
            job.worker_token = token
            job.lease_expires_at = now + timedelta(seconds=self.lease_seconds)
            job.attempt_count += 1
            job.started_at = job.started_at or now
            job.last_error_code = None
            return {
                "token": token,
                "processed_rows": job.processed_rows,
                "chunk_size": job.chunk_size,
                "total_rows": job.total_rows,
                "upload_id": upload.id,
                "byte_size": upload.byte_size,
                "sha256": upload.sha256,
                "uploaded_by_id": job.uploaded_by_id,
            }

    def _mark_failed(
        self,
        job_id: uuid.UUID,
        organization_id: uuid.UUID,
        token: uuid.UUID,
        code: str,
    ) -> None:
        now = datetime.now(UTC)
        with self.session_factory.begin() as session:
            _set_tenant_context(session, organization_id)
            job = session.scalar(
                select(AudienceImportJob)
                .where(
                    AudienceImportJob.organization_id == organization_id,
                    AudienceImportJob.id == job_id,
                )
                .with_for_update()
            )
            if job is None or job.worker_token != token:
                return
            job.status = "failed"
            job.last_error_code = code
            job.completed_at = now
            job.worker_token = None
            job.lease_expires_at = None

    def _release_for_retry(
        self,
        job_id: uuid.UUID,
        organization_id: uuid.UUID,
        token: uuid.UUID,
    ) -> None:
        try:
            with self.session_factory.begin() as session:
                _set_tenant_context(session, organization_id)
                job = session.scalar(
                    select(AudienceImportJob)
                    .where(
                        AudienceImportJob.organization_id == organization_id,
                        AudienceImportJob.id == job_id,
                    )
                    .with_for_update()
                )
                if job is not None and job.worker_token == token:
                    job.status = "queued"
                    job.last_error_code = "PROCESSING_RETRY_PENDING"
                    job.worker_token = None
                    job.lease_expires_at = None
        except Exception:
            logger.exception(
                "Could not release audience import lease",
                extra={"audience_import_job_id": str(job_id)},
            )

    def process(
        self,
        job_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> dict[str, str | int]:
        claim = self._claim(job_id, organization_id)
        if claim is None:
            return {"status": "not_claimed"}

        token = claim["token"]
        upload_path = self.storage_dir / f"{claim['upload_id'].hex}.csv"
        try:
            if upload_path.is_symlink() or not upload_path.is_file():
                raise UploadProcessingError("UPLOAD_FILE_UNAVAILABLE")

            actual_size, actual_digest = _file_digest(upload_path)
            if actual_size != claim["byte_size"] or actual_digest != claim["sha256"]:
                raise UploadProcessingError("UPLOAD_CHECKSUM_MISMATCH")

            with upload_path.open("r", encoding="utf-8-sig", newline="") as source:
                reader = csv.reader(source, strict=True)
                raw_headers = next(reader, None)
                if not raw_headers:
                    raise UploadProcessingError("UPLOAD_HEADER_MISSING")
                headers = [header.strip().casefold() for header in raw_headers]
                if (
                    any(header not in _ALLOWED_HEADERS for header in headers)
                    or len(headers) != len(set(headers))
                    or "full_name" not in headers
                    or not {"email", "phone"}.intersection(headers)
                ):
                    raise UploadProcessingError("UPLOAD_HEADER_INVALID")

                row_iterator = _iter_nonblank_rows(reader)
                for _ in range(claim["processed_rows"]):
                    if next(row_iterator, None) is None:
                        raise UploadProcessingError("UPLOAD_CHECKPOINT_INVALID")

                while True:
                    with self.session_factory.begin() as session:
                        _set_tenant_context(session, organization_id)
                        job = session.scalar(
                            select(AudienceImportJob)
                            .where(
                                AudienceImportJob.organization_id == organization_id,
                                AudienceImportJob.id == job_id,
                            )
                            .with_for_update()
                        )
                        if job is None or job.worker_token != token:
                            return {"status": "lease_lost"}

                        batch = []
                        for _ in range(job.chunk_size):
                            item = next(row_iterator, None)
                            if item is None:
                                break
                            row_number, values = item
                            if len(values) != len(headers):
                                raise UploadProcessingError("UPLOAD_ROW_SHAPE_INVALID")
                            batch.append(
                                (row_number, dict(zip(headers, values, strict=True)))
                            )

                        if not batch:
                            now = datetime.now(UTC)
                            if job.processed_rows != job.total_rows:
                                job.status = "failed"
                                job.last_error_code = "UPLOAD_ROW_COUNT_MISMATCH"
                            else:
                                job.status = (
                                    "completed_with_errors"
                                    if job.error_rows
                                    else "completed"
                                )
                                job.last_error_code = None
                            job.completed_at = now
                            job.worker_token = None
                            job.lease_expires_at = None
                            return {
                                "status": job.status,
                                "processed_rows": job.processed_rows,
                            }

                        imported_in_chunk = 0
                        errors_in_chunk = 0
                        duplicates_in_chunk = 0
                        actor_id = claim["uploaded_by_id"]
                        for row_number, row in batch:
                            validated = _validate_contact_row(row)
                            if isinstance(validated, list):
                                session.add_all(
                                    [
                                        AudienceImportJobError(
                                            organization_id=organization_id,
                                            job_id=job_id,
                                            row_number=row_number,
                                            field_name=issue["field_name"],
                                            error_code=issue["error_code"],
                                        )
                                        for issue in validated
                                    ]
                                )
                                # Progress is measured in rejected source rows,
                                # not the number of field-level issue records.
                                errors_in_chunk += 1
                                continue

                            duplicate_issue = _find_duplicate_issue(
                                session,
                                organization_id,
                                validated,
                            )
                            if duplicate_issue is not None:
                                session.add(
                                    AudienceImportJobError(
                                        organization_id=organization_id,
                                        job_id=job_id,
                                        row_number=row_number,
                                        field_name=duplicate_issue["field_name"],
                                        error_code=duplicate_issue["error_code"],
                                    )
                                )
                                duplicates_in_chunk += 1
                                continue

                            member = AudienceMember(
                                organization_id=organization_id,
                                created_by=actor_id,
                                updated_by=actor_id,
                                **validated,
                            )
                            try:
                                # A database uniqueness race can occur after the
                                # pre-check. Isolate the insert so one race does
                                # not roll back the rest of the bounded chunk.
                                with session.begin_nested():
                                    session.add(member)
                                    session.flush()
                            except IntegrityError as error:
                                if not is_identity_unique_violation(error):
                                    raise
                                duplicate_issue = _find_duplicate_issue(
                                    session,
                                    organization_id,
                                    validated,
                                )
                                if duplicate_issue is None:
                                    raise
                                session.add(
                                    AudienceImportJobError(
                                        organization_id=organization_id,
                                        job_id=job_id,
                                        row_number=row_number,
                                        field_name=duplicate_issue["field_name"],
                                        error_code=duplicate_issue["error_code"],
                                    )
                                )
                                duplicates_in_chunk += 1
                                continue
                            imported_in_chunk += 1

                        job.processed_rows += len(batch)
                        job.imported_rows += imported_in_chunk
                        job.error_rows += errors_in_chunk
                        job.duplicate_rows += duplicates_in_chunk
                        job.lease_expires_at = datetime.now(UTC) + timedelta(
                            seconds=self.lease_seconds
                        )

        except UploadProcessingError as error:
            self._mark_failed(job_id, organization_id, token, error.code)
            return {"status": "failed", "error_code": error.code}
        except (csv.Error, UnicodeDecodeError, StopIteration):
            self._mark_failed(
                job_id,
                organization_id,
                token,
                "UPLOAD_CSV_UNREADABLE",
            )
            return {"status": "failed", "error_code": "UPLOAD_CSV_UNREADABLE"}
        except Exception:
            self._release_for_retry(job_id, organization_id, token)
            raise

    def mark_retry_exhausted(
        self,
        job_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> None:
        now = datetime.now(UTC)
        with self.session_factory.begin() as session:
            _set_tenant_context(session, organization_id)
            job = session.scalar(
                select(AudienceImportJob)
                .where(
                    AudienceImportJob.organization_id == organization_id,
                    AudienceImportJob.id == job_id,
                )
                .with_for_update()
            )
            if job is None or job.status in _TERMINAL_STATUSES:
                return
            job.status = "failed"
            job.last_error_code = "WORKER_RETRIES_EXHAUSTED"
            job.completed_at = now
            job.worker_token = None
            job.lease_expires_at = None
