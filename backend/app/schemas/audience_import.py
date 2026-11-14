import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

ImportJobStatus = Literal[
    "queued", "processing", "completed", "completed_with_errors", "failed"
]


class AudienceImportUploadResponse(BaseModel):
    """Accepted upload and the import job created from it."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    byte_size: int
    row_count: int
    sha256: str
    created_at: datetime
    job_id: uuid.UUID
    status: ImportJobStatus
    total_rows: int
    processed_rows: int
    imported_rows: int
    error_rows: int
    duplicate_rows: int


class AudienceImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    upload_id: uuid.UUID
    organization_id: uuid.UUID
    status: ImportJobStatus
    total_rows: int
    processed_rows: int
    imported_rows: int
    error_rows: int
    duplicate_rows: int
    chunk_size: int
    last_error_code: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class AudienceImportErrorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    row_number: int
    field_name: str | None
    error_code: str
    created_at: datetime


class AudienceImportErrorsPagination(BaseModel):
    next_cursor: str | None
    has_more: bool
    limit: int


class AudienceImportErrorsResponse(BaseModel):
    job_id: uuid.UUID
    data: list[AudienceImportErrorResponse]
    pagination: AudienceImportErrorsPagination
