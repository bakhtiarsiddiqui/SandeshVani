import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, ensure_utc
from app.db.session import set_tenant_context
from app.models.membership import Membership
from app.models.organization import Organization
from app.models.role import Role
from app.repositories.membership_repo import MembershipRepository
from app.repositories.organization_repo import OrganizationRepository
from app.repositories.role_repo import RoleRepository
from app.repositories.session_repo import SessionRepository
from app.repositories.user_repo import UserRepository


class OrganizationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.org_repo = OrganizationRepository(session)
        self.membership_repo = MembershipRepository(session)
        self.role_repo = RoleRepository(session)
        self.user_repo = UserRepository(session)
        self.session_repo = SessionRepository(session)

    async def create_organization(
        self, name: str, slug: str, creator_user_id: uuid.UUID
    ) -> Organization:
        """Controlled organization provisioning.

        Performs atomic provisioning:
        1. Create the organization.
        2. Create creator's active membership.
        3. Create the organization's default system roles.
        4. Assign the Organization Administrator role to the creator.
        5. Commit only after all operations succeed.
        If any operation fails, the transaction rolls back.
        """
        clean_slug = slug.strip().lower()
        existing = await self.org_repo.get_by_slug(clean_slug)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Organization slug '{clean_slug}' is already in use",
            )

        # Ensure global permissions exist independently
        await self.role_repo.seed_global_permissions()

        try:
            # 1. Create the organization
            org = await self.org_repo.create(
                name=name.strip(),
                slug=clean_slug,
            )

            # Establish tenant context for the new organization so RLS allows queries
            await set_tenant_context(self.session, org.id)

            # 2. Create creator active membership
            membership = await self.membership_repo.create_membership(
                organization_id=org.id,
                user_id=creator_user_id,
                status="active",
            )

            # 3. Create the organization's default system roles
            org_roles = await self.role_repo.seed_organization_roles(org.id)

            # 4. Assign Organization Administrator role to creator
            admin_role = org_roles.get("Organization Administrator")
            if not admin_role:
                raise RuntimeError(
                    "Failed to provision Organization Administrator role"
                )

            await self.membership_repo.assign_role(
                organization_id=org.id,
                membership_id=membership.id,
                role_id=admin_role.id,
                assigned_by=creator_user_id,
            )

            # 5. Commit only after all operations succeed
            await self.session.commit()
            return org
        except Exception:
            await self.session.rollback()
            raise

    async def get_user_organizations(self, user_id: uuid.UUID) -> list[Organization]:
        return await self.org_repo.get_user_organizations(user_id)

    async def get_organization(
        self, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> Organization:
        await set_tenant_context(self.session, organization_id)
        membership = await self.membership_repo.get_membership(organization_id, user_id)
        if not membership or membership.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not an active member of this organization",
            )
        org = await self.org_repo.get_by_id(organization_id)
        if not org or org.status != "active":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found or inactive",
            )
        return org

    async def get_effective_permissions(
        self, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[str]:
        await set_tenant_context(self.session, organization_id)
        membership = await self.membership_repo.get_membership(organization_id, user_id)
        if not membership or membership.status != "active":
            return []
        role_ids = [mr.role_id for mr in membership.membership_roles]
        return await self.role_repo.get_permissions_for_roles(
            role_ids, organization_id=organization_id
        )

    async def get_organization_members(
        self, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[Membership]:
        perms = await self.get_effective_permissions(organization_id, user_id)
        if "members:read" not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission 'members:read' required",
            )
        return await self.membership_repo.get_organization_members(organization_id)

    async def add_member(
        self,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        email: str,
        role_ids: list[uuid.UUID],
    ) -> Membership:
        perms = await self.get_effective_permissions(organization_id, actor_user_id)
        if "members:create" not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission 'members:create' required",
            )

        invitee = await self.user_repo.get_by_normalized_email(email.strip().lower())
        if not invitee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found. Invitees must register first.",
            )

        existing_membership = await self.membership_repo.get_membership(
            organization_id, invitee.id
        )
        if existing_membership:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this organization",
            )

        membership = await self.membership_repo.create_membership(
            organization_id=organization_id,
            user_id=invitee.id,
            status="active",
        )

        for r_id in role_ids:
            await self.membership_repo.assign_role(
                organization_id=organization_id,
                membership_id=membership.id,
                role_id=r_id,
                assigned_by=actor_user_id,
            )

        return membership

    async def assign_role_to_member(
        self,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        membership_id: uuid.UUID,
        role_id: uuid.UUID,
    ) -> None:
        perms = await self.get_effective_permissions(organization_id, actor_user_id)
        if "roles:assign" not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission 'roles:assign' required",
            )

        membership = await self.membership_repo.get_membership_by_id(membership_id)
        if not membership or membership.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Membership does not belong to this organization",
            )

        try:
            await self.membership_repo.assign_role(
                organization_id=organization_id,
                membership_id=membership_id,
                role_id=role_id,
                assigned_by=actor_user_id,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from e

    async def remove_role_from_member(
        self,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        membership_id: uuid.UUID,
        role_id: uuid.UUID,
    ) -> None:
        perms = await self.get_effective_permissions(organization_id, actor_user_id)
        if "roles:assign" not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission 'roles:assign' required",
            )

        membership = await self.membership_repo.get_membership_by_id(membership_id)
        if not membership or membership.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Membership does not belong to this organization",
            )

        # Serialize administrator-role removals for this organization.
        # This prevents concurrent requests from both removing the final role.
        organization_lock = await self.session.execute(
            select(Organization.id)
            .where(Organization.id == organization_id)
            .with_for_update()
        )
        if organization_lock.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )

        role = await self.role_repo.get_role_by_id(role_id)
        holds_admin_role = (
            role is not None
            and role.organization_id == organization_id
            and role.scope == "organization"
            and role.name.strip().casefold() == "organization administrator"
            and any(item.role_id == role_id for item in membership.membership_roles)
        )
        if holds_admin_role:
            active_admins = await self.membership_repo.count_active_members_with_role(
                organization_id, role_id
            )
            if active_admins <= 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "The last active organization administrator cannot be removed"
                    ),
                )

        removed = await self.membership_repo.remove_role(
            organization_id, membership_id, role_id
        )
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role assignment not found",
            )

    async def switch_organization_context(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        target_organization_id: uuid.UUID,
    ) -> dict:
        auth_session = await self.session_repo.get_session(session_id)
        if (
            auth_session is None
            or auth_session.user_id != user_id
            or auth_session.revoked_at is not None
            or ensure_utc(auth_session.expires_at) <= datetime.now(UTC)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been revoked or expired",
            )

        await set_tenant_context(self.session, target_organization_id)
        membership = await self.membership_repo.get_membership(
            target_organization_id, user_id
        )
        if not membership or membership.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not an active member of this organization",
            )

        org = await self.org_repo.get_by_id(target_organization_id)
        if not org or org.status != "active":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found or inactive",
            )

        active_roles: list[Role] = []
        role_ids = [mr.role_id for mr in membership.membership_roles]
        for r_id in role_ids:
            r = await self.role_repo.get_role_by_id(r_id)
            if r:
                active_roles.append(r)

        perms = await self.role_repo.get_permissions_for_roles(
            role_ids, organization_id=target_organization_id
        )

        auth_session.selected_organization_id = target_organization_id
        await self.session.flush()

        new_access_token = create_access_token(
            user_id=str(user_id),
            session_id=str(session_id),
            org_id=str(target_organization_id),
        )

        return {
            "access_token": new_access_token,
            "active_organization": org,
            "roles": active_roles,
            "permissions": perms,
        }
