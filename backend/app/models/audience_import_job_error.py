import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class AudienceImportJobError(Base, UUIDPrimaryKeyMixin):
    """PII-minimized validation errors for one logical CSV data row."""

    __tablename__ = "audience_import_job_errors"
    __table_args__ = (
        CheckConstraint(
            "row_number >= 2",
            name="ck_audience_import_job_errors_row_number",
        ),
        ForeignKeyConstraint(
            ["organization_id", "job_id"],
            ["audience_import_jobs.organization_id", "audience_import_jobs.id"],
            name="fk_audience_import_job_errors_tenant_job",
            ondelete="CASCADE",
        ),
        Index(
            "ix_audience_import_job_errors_org_job_row",
            "organization_id",
            "job_id",
            "row_number",
            "id",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    field_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_code: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
