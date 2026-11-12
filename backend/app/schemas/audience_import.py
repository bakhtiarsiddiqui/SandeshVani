import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class AudienceImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    upload_id: uuid.UUID
    status: Literal[
        "queued",
        "processing",
        "completed",
        "completed_with_errors",
        "failed",
    ]
    total_rows: int
    processed_rows: int
    imported_rows: int
    rejected_rows: int
    failure_code: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class AudienceImportJobErrorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    row_number: int
    field_name: str | None
    error_code: str
    created_at: datetime


class AudienceImportErrorPagination(BaseModel):
    next_cursor: str | None
    has_more: bool
    limit: int


class AudienceImportJobErrorListResponse(BaseModel):
    data: list[AudienceImportJobErrorResponse]
    pagination: AudienceImportErrorPagination
