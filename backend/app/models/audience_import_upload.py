import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class AudienceImportUpload(Base, UUIDPrimaryKeyMixin):
    """Tenant-owned metadata for a validated, privately stored audience CSV."""

    __tablename__ = "audience_import_uploads"
    __table_args__ = (
        CheckConstraint("byte_size > 0", name="ck_audience_import_uploads_byte_size"),
        CheckConstraint("row_count > 0", name="ck_audience_import_uploads_row_count"),
        CheckConstraint(
            "length(sha256) = 64",
            name="ck_audience_import_uploads_sha256_length",
        ),
        UniqueConstraint(
            "organization_id",
            "id",
            name="uq_audience_import_uploads_org_id",
        ),
        Index(
            "ix_audience_import_uploads_org_created",
            "organization_id",
            "created_at",
        ),
        Index(
            "ix_audience_import_uploads_org_retention",
            "organization_id",
            "retention_expires_at",
            "file_deleted_at",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    retention_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC) + timedelta(days=30),
        nullable=False,
    )
    file_deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
