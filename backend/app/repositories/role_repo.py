import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.role import Permission, Role, RolePermission

# Standard baseline permissions from RBAC_MATRIX.md
BASELINE_PERMISSIONS = [
    # Identity / Organization
    ("organization:read", "View own organization details"),
    ("organization:update", "Update own organization settings"),
    ("members:read", "View organization members"),
    ("members:create", "Invite or add new organization members"),
    ("members:update", "Update member status"),
    ("members:deactivate", "Deactivate organization members"),
    ("roles:read", "View organization roles"),
    ("roles:assign", "Assign or revoke roles for organization members"),
    ("permissions:read", "View permissions catalog"),
    # Audience
    ("audiences:read", "View audience members and lists"),
    ("audiences:create", "Create or import audience members"),
    ("audiences:update", "Update audience members"),
    ("audiences:import", "Import audience CSV"),
    ("segments:read", "View audience segments"),
    ("segments:create", "Create audience segments"),
    ("consent:read", "View consent records"),
    ("consent:update", "Update consent records"),
    ("suppression:read", "View channel suppression evidence"),
    ("suppression:update", "Record or lift channel suppression"),
    ("segments:update", "Update audience segment versions"),
    # Campaign / Governance
    ("campaigns:read", "View campaigns and versions"),
    ("campaigns:create", "Create new campaigns"),
    ("campaigns:update", "Edit draft campaigns"),
    ("campaigns:submit", "Submit campaigns for approval"),
    ("campaigns:cancel", "Cancel active campaigns"),
    ("approvals:read", "View pending approvals"),
    ("approvals:approve", "Approve campaign versions"),
    ("approvals:reject", "Reject campaign versions"),
    # Templates / Distribution / Analytics
    ("templates:read", "View message templates"),
    ("templates:create", "Create message templates"),
    ("templates:update", "Create immutable template versions"),
    ("campaigns:content:update", "Author campaign content variants"),
    ("localization:read", "View language variants"),
    ("localization:update", "Author language variants"),
    ("distribution:mock_execute", "Execute mock campaign dispatch"),
    ("analytics:read", "View campaign and delivery analytics"),
    ("audit:read", "View audit logs"),
]

# Baseline role grants
ROLE_PERMISSIONS_MAP = {
    "Organization Administrator": [
        "organization:read",
        "organization:update",
        "members:read",
        "members:create",
        "members:update",
        "members:deactivate",
        "roles:read",
        "roles:assign",
        "permissions:read",
        "audiences:read",
        "audiences:create",
        "audiences:update",
        "audiences:import",
        "segments:read",
        "segments:create",
        "consent:read",
        "consent:update",
        "suppression:read",
        "suppression:update",
        "segments:update",
        "templates:update",
        "campaigns:content:update",
        "localization:read",
        "localization:update",
        "campaigns:read",
        "campaigns:create",
        "campaigns:update",
        "campaigns:submit",
        "campaigns:cancel",
        "templates:read",
        "templates:create",
        "distribution:mock_execute",
        "analytics:read",
        "audit:read",
    ],
    "Campaign Manager": [
        "organization:read",
        "audiences:read",
        "audiences:create",
        "audiences:update",
        "audiences:import",
        "segments:read",
        "segments:create",
        "segments:update",
        "campaigns:read",
        "campaigns:content:update",
        "localization:read",
        "campaigns:create",
        "campaigns:update",
        "campaigns:submit",
        "templates:read",
        "distribution:mock_execute",
        "analytics:read",
    ],
    "Communication Team": [
        "organization:read",
        "audiences:read",
        "templates:read",
        "templates:create",
        "campaigns:read",
        "campaigns:content:update",
        "templates:update",
        "localization:read",
        "localization:update",
        "analytics:read",
    ],
    "Approver": [
        "organization:read",
        "campaigns:read",
        "approvals:read",
        "approvals:approve",
        "approvals:reject",
        "analytics:read",
    ],
}


class RoleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_role_by_id(self, role_id: uuid.UUID) -> Role | None:
        stmt = (
            select(Role)
            .where(Role.id == role_id)
            .options(selectinload(Role.permissions))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_role_by_name(
        self,
        name: str,
        organization_id: uuid.UUID | None = None,
        scope: str = "organization",
    ) -> Role | None:
        clean_name = name.strip().lower()
        if scope == "organization":
            if not organization_id:
                raise ValueError(
                    "organization_id is required for organization-scoped role lookup"
                )
            stmt = (
                select(Role)
                .where(
                    Role.scope == "organization",
                    Role.organization_id == organization_id,
                    func.lower(Role.name) == clean_name,
                )
                .options(selectinload(Role.permissions))
            )
        elif scope == "platform":
            if organization_id is not None:
                raise ValueError(
                    "organization_id must be None for platform-scoped role lookup"
                )
            stmt = (
                select(Role)
                .where(
                    Role.scope == "platform",
                    Role.organization_id.is_(None),
                    func.lower(Role.name) == clean_name,
                )
                .options(selectinload(Role.permissions))
            )
        else:
            raise ValueError(
                f"Invalid scope: {scope}. Must be 'organization' or 'platform'"
            )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_organization_roles(self, organization_id: uuid.UUID) -> list[Role]:
        stmt = (
            select(Role)
            .where(
                Role.scope == "organization",
                Role.organization_id == organization_id,
            )
            .options(selectinload(Role.permissions))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_permissions_for_roles(
        self,
        role_ids: list[uuid.UUID],
        organization_id: uuid.UUID | None = None,
    ) -> list[str]:
        if not role_ids:
            return []

        # Do not infer tenant authority from session.info. PostgreSQL's tenant
        # setting is transaction-local, whereas Python session metadata can
        # survive a rollback. Callers must pass the organization only after
        # membership verification; without it, resolve platform grants only.
        if organization_id is not None:
            scope_filter = or_(
                and_(
                    Role.scope == "platform",
                    RolePermission.role_scope == "platform",
                ),
                and_(
                    Role.scope == "organization",
                    RolePermission.role_scope == "organization",
                    Role.organization_id == organization_id,
                    RolePermission.organization_id == organization_id,
                ),
            )
        else:
            scope_filter = and_(
                Role.scope == "platform",
                RolePermission.role_scope == "platform",
            )

        stmt = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .where(
                RolePermission.role_id.in_(role_ids),
                scope_filter,
            )
            .distinct()
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def assign_permission_to_role(
        self,
        role: Role,
        permission_id: uuid.UUID,
    ) -> RolePermission:
        """Assign a permission to a role idempotently with appropriate scope."""
        stmt = select(RolePermission).where(
            RolePermission.role_id == role.id,
            RolePermission.permission_id == permission_id,
        )
        existing = await self.session.execute(stmt)
        rp = existing.scalar_one_or_none()
        if not rp:
            rp = RolePermission(
                role_id=role.id,
                permission_id=permission_id,
                role_scope=role.scope,
                organization_id=(
                    role.organization_id if role.scope == "organization" else None
                ),
            )
            self.session.add(rp)
            await self.session.flush()
        return rp

    async def seed_global_permissions(self) -> dict[str, Permission]:
        """Seed baseline permissions independently from roles."""
        perm_map: dict[str, Permission] = {}
        for code, description in BASELINE_PERMISSIONS:
            existing = await self.session.execute(
                select(Permission).where(Permission.code == code)
            )
            perm = existing.scalar_one_or_none()
            if not perm:
                perm = Permission(code=code, description=description)
                self.session.add(perm)
                await self.session.flush()
            perm_map[code] = perm
        return perm_map

    async def seed_organization_roles(
        self, organization_id: uuid.UUID
    ) -> dict[str, Role]:
        """Seed organization-scoped default system roles for a specific organization."""
        perm_map = await self.seed_global_permissions()

        org_roles: dict[str, Role] = {}
        for role_name, allowed_perms in ROLE_PERMISSIONS_MAP.items():
            existing = await self.session.execute(
                select(Role).where(
                    Role.organization_id == organization_id,
                    Role.scope == "organization",
                    func.lower(Role.name) == role_name.lower(),
                )
            )
            role = existing.scalar_one_or_none()
            if not role:
                role = Role(
                    name=role_name,
                    description=f"Standard organization role: {role_name}",
                    is_system_role=True,
                    organization_id=organization_id,
                    scope="organization",
                )
                self.session.add(role)
                await self.session.flush()

            # Associate permissions idempotently
            for p_code in allowed_perms:
                if p_code in perm_map:
                    await self.assign_permission_to_role(role, perm_map[p_code].id)

            org_roles[role_name] = role

        return org_roles

    async def seed_defaults(self) -> None:
        """Seed baseline permissions only.

        Organization-scoped roles must be seeded per organization via
        seed_organization_roles. Platform roles are managed separately.
        """
        await self.seed_global_permissions()
