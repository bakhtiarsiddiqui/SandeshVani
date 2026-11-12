import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AudienceImportUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    byte_size: int
    row_count: int
    sha256: str
    created_at: datetime
