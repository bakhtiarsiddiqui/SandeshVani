import uuid

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AudienceMember(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A tenant-owned contact record addressable by one or more channels."""

    __tablename__ = "audience_members"
    __table_args__ = (
        CheckConstraint(
            "length(trim(full_name)) > 0",
            name="ck_audience_members_full_name",
        ),
        CheckConstraint(
            "email IS NOT NULL OR phone IS NOT NULL",
            name="ck_audience_members_contact_point",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_audience_members_status",
        ),
        CheckConstraint(
            "preferred_language IN ('en', 'hi')",
            name="ck_audience_members_language",
        ),
        UniqueConstraint(
            "organization_id", "id", name="uq_audience_members_org_id"
        ),
        Index(
            "ix_audience_members_org_created",
            "organization_id",
            "created_at",
            "id",
        ),
        Index(
            "ix_audience_members_org_status",
            "organization_id",
            "status",
        ),
        Index(
            "ix_audience_members_org_district",
            "organization_id",
            "district",
        ),
        Index(
            "ix_audience_members_org_language",
            "organization_id",
            "preferred_language",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(16), nullable=True)
    preferred_language: Mapped[str] = mapped_column(
        String(12), default="en", nullable=False
    )
    district: Mapped[str | None] = mapped_column(String(150), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
