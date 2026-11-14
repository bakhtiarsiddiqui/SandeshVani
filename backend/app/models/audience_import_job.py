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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AudienceImportJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Durable, tenant-scoped state for one CSV audience import."""

    __tablename__ = "audience_import_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'processing', 'completed', "
            "'completed_with_errors', 'failed')",
            name="ck_audience_import_jobs_status",
        ),
        CheckConstraint("total_rows > 0", name="ck_audience_import_jobs_total_rows"),
        CheckConstraint(
            "processed_rows >= 0 AND processed_rows <= total_rows",
            name="ck_audience_import_jobs_processed_rows",
        ),
        CheckConstraint(
            "imported_rows >= 0 AND error_rows >= 0 AND duplicate_rows >= 0",
            name="ck_audience_import_jobs_result_rows",
        ),
        CheckConstraint(
            "processed_rows = imported_rows + error_rows + duplicate_rows",
            name="ck_audience_import_jobs_row_accounting",
        ),
        CheckConstraint("chunk_size > 0", name="ck_audience_import_jobs_chunk_size"),
        ForeignKeyConstraint(
            ["organization_id", "upload_id"],
            [
                "audience_import_uploads.organization_id",
                "audience_import_uploads.id",
            ],
            name="fk_audience_import_jobs_tenant_upload",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "organization_id",
            "id",
            name="uq_audience_import_jobs_org_id",
        ),
        UniqueConstraint(
            "organization_id",
            "upload_id",
            name="uq_audience_import_jobs_org_upload",
        ),
        Index(
            "ix_audience_import_jobs_org_status_created",
            "organization_id",
            "status",
            "created_at",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    upload_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(24),
        default="queued",
        nullable=False,
    )
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    processed_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    imported_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_rows: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    chunk_size: Mapped[int] = mapped_column(Integer, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    worker_token: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
