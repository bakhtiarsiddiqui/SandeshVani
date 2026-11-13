import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    UniqueConstraint,
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
        UniqueConstraint(
            "organization_id",
            "job_id",
            "row_number",
            name="uq_audience_import_job_errors_job_row",
        ),
        Index(
            "ix_audience_import_job_errors_org_job_row",
            "organization_id",
            "job_id",
            "row_number",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    errors: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
