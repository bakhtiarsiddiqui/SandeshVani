import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.membership import Membership
    from app.models.organization import Organization
    from app.models.user import User


class Permission(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    description: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="role_permissions",
        primaryjoin="Permission.id == foreign(RolePermission.permission_id)",
        secondaryjoin="Role.id == foreign(RolePermission.role_id)",
        back_populates="permissions",
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        CheckConstraint(
            "(role_scope = 'organization' AND organization_id IS NOT NULL) OR "
            "(role_scope = 'platform' AND organization_id IS NULL)",
            name="ck_role_permissions_scope_org_id",
        ),
        ForeignKeyConstraint(
            ["organization_id", "role_id"],
            ["roles.organization_id", "roles.id"],
            name="fk_role_permissions_composite_org_role",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["role_scope", "role_id"],
            ["roles.scope", "roles.id"],
            name="fk_role_permissions_composite_scope_role",
            ondelete="CASCADE",
        ),
    )

    role_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )
    role_scope: Mapped[str] = mapped_column(String(20), nullable=False)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True,
        index=True,
    )


class Role(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "roles"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    is_system_role: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "(scope = 'organization' AND organization_id IS NOT NULL) OR "
            "(scope = 'platform' AND organization_id IS NULL)",
            name="ck_roles_scope_org_id",
        ),
        UniqueConstraint("organization_id", "id", name="uq_roles_org_id"),
        UniqueConstraint("scope", "id", name="uq_roles_scope_id"),
        Index(
            "uq_roles_org_name_ci",
            organization_id,
            func.lower(name),
            unique=True,
            postgresql_where=text("scope = 'organization'"),
            sqlite_where=text("scope = 'organization'"),
        ),
        Index(
            "uq_roles_platform_name_ci",
            func.lower(name),
            unique=True,
            postgresql_where=text("scope = 'platform'"),
            sqlite_where=text("scope = 'platform'"),
        ),
    )

    organization: Mapped["Organization | None"] = relationship(
        "Organization", back_populates="roles"
    )
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission",
        secondary="role_permissions",
        primaryjoin="Role.id == foreign(RolePermission.role_id)",
        secondaryjoin="Permission.id == foreign(RolePermission.permission_id)",
        back_populates="roles",
    )


class MembershipRole(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "membership_roles"
    __table_args__ = (
        UniqueConstraint(
            "membership_id", "role_id", name="uq_membership_roles_member_role"
        ),
        ForeignKeyConstraint(
            ["organization_id", "membership_id"],
            ["memberships.organization_id", "memberships.id"],
            name="fk_membership_roles_composite_org_membership",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["organization_id", "role_id"],
            ["roles.organization_id", "roles.id"],
            name="fk_membership_roles_composite_org_role",
            ondelete="CASCADE",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
        index=True,
    )
    membership_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
        index=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
        index=True,
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    membership: Mapped["Membership"] = relationship(
        "Membership",
        primaryjoin="MembershipRole.membership_id == Membership.id",
        foreign_keys=[membership_id],
        back_populates="membership_roles",
    )
    role: Mapped["Role"] = relationship("Role", overlaps="membership_roles")


class PlatformRoleAssignment(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "platform_role_assignments"
    __table_args__ = (
        CheckConstraint(
            "role_scope = 'platform'",
            name="ck_platform_role_assignments_role_scope",
        ),
        UniqueConstraint("user_id", "role_id", name="uq_platform_roles_user_role"),
        ForeignKeyConstraint(
            ["role_scope", "role_id"],
            ["roles.scope", "roles.id"],
            name="fk_platform_role_assignments_composite_scope_role",
            ondelete="CASCADE",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_scope: Mapped[str] = mapped_column(
        String(20),
        default="platform",
        server_default="platform",
        nullable=False,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
        index=True,
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="platform_roles",
    )
    role: Mapped["Role"] = relationship("Role")
