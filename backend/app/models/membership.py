import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.role import MembershipRole
    from app.models.user import User


class Membership(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_memberships_org_user"),
        UniqueConstraint("organization_id", "id", name="uq_memberships_org_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50), default="active", nullable=False, index=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="memberships"
    )
    user: Mapped["User"] = relationship("User", back_populates="memberships")
    membership_roles: Mapped[list["MembershipRole"]] = relationship(
        "MembershipRole",
        primaryjoin="Membership.id == MembershipRole.membership_id",
        foreign_keys="[MembershipRole.membership_id]",
        back_populates="membership",
        cascade="all, delete-orphan",
    )
