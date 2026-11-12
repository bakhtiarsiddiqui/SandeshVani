import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint
from sqlalchemy import Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class AudienceImportJob(Base, UUIDPrimaryKeyMixin):
    """Tenant-scoped processing state for one validated audience CSV upload."""

    __tablename__ = "audience_import_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'processing', 'completed', "
            "'completed_with_errors', 'failed')",
            name="ck_audience_import_jobs_status",
        ),
        CheckConstraint("total_rows > 0", name="ck_audience_import_jobs_total_rows"),
        CheckConstraint(
            "processed_rows >= 0 AND imported_rows >= 0 AND rejected_rows >= 0",
            name="ck_audience_import_jobs_nonnegative_counts",
        ),
        CheckConstraint(
            "processed_rows <= total_rows",
            name="ck_audience_import_jobs_processed_limit",
        ),
        CheckConstraint(
            "imported_rows + rejected_rows = processed_rows",
            name="ck_audience_import_jobs_count_balance",
        ),
        UniqueConstraint("organization_id", "id", name="uq_audience_import_jobs_org_id"),
        UniqueConstraint(
            "organization_id", "upload_id", name="uq_audience_import_jobs_org_upload"
        ),
        ForeignKeyConstraint(
            ["organization_id", "upload_id"],
            ["audience_import_uploads.organization_id", "audience_import_uploads.id"],
            name="fk_audience_import_jobs_org_upload",
            ondelete="CASCADE",
        ),
        Index("ix_audience_import_jobs_org_created", "organization_id", "created_at", "id"),
        Index("ix_audience_import_jobs_status_updated", "status", "updated_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    upload_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(32), default="queued", server_default="queued", nullable=False
    )
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    processed_rows: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    imported_rows: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    rejected_rows: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    failure_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
