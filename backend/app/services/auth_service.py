import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_csrf_token,
    ensure_utc,
    generate_secure_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.organization import Organization
from app.models.role import Role
from app.models.user import User
from app.repositories.membership_repo import MembershipRepository
from app.repositories.organization_repo import OrganizationRepository
from app.repositories.role_repo import RoleRepository
from app.repositories.session_repo import SessionRepository
from app.repositories.user_repo import UserRepository

logger = logging.getLogger("sandeshvani.auth")


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.session_repo = SessionRepository(session)
        self.org_repo = OrganizationRepository(session)
        self.membership_repo = MembershipRepository(session)
        self.role_repo = RoleRepository(session)

    async def register(
        self, email: str, password: str, full_name: str
    ) -> tuple[User, str]:
        """Register a new user with pending verification status.

        Does NOT automatically assign organization memberships or admin privileges.
        Returns the user and a secure opaque verification token.
        """
        normalized_email = email.strip().lower()

        existing = await self.user_repo.get_by_normalized_email(normalized_email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email address already exists",
            )

        # Hash password using Argon2id
        p_hash = hash_password(password)

        user = await self.user_repo.create(
            email=email.strip(),
            normalized_email=normalized_email,
            password_hash=p_hash,
            full_name=full_name.strip(),
            status="pending_verification",
        )

        # Generate opaque email verification token
        raw_token = generate_secure_token(32)
        t_hash = hash_token(raw_token)
        await self.session_repo.create_email_token(
            user_id=user.id,
            token_hash=t_hash,
            expires_hours=24,
        )

        return user, raw_token

    async def verify_email(self, token: str) -> User:
        """Verify user's email address using the opaque token."""
        t_hash = hash_token(token)
        token_record = await self.session_repo.get_email_token_by_hash(t_hash)

        if not token_record or not await self.session_repo.consume_email_token(
            token_record.id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )

        # The conditional UPDATE makes token consumption atomic across workers.
        await self.user_repo.mark_email_verified(token_record.user_id)

        user = await self.user_repo.get_by_id(token_record.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return user

    async def resend_verification(self, email: str) -> str | None:
        """Issue a new verification token if user exists and is unverified."""
        normalized_email = email.strip().lower()
        raw_token = generate_secure_token(32)
        t_hash = hash_token(raw_token)
        user = await self.user_repo.get_by_normalized_email(normalized_email)
        if not user or user.status != "pending_verification":
            # Return None silently to avoid email enumeration
            return None

        await self.session_repo.create_email_token(
            user_id=user.id, token_hash=t_hash, expires_hours=24
        )
        return raw_token

    async def login(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Authenticate user, create session, and issue access token."""
        normalized_email = email.strip().lower()
        user = await self.user_repo.get_by_normalized_email(normalized_email)

        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        # Check account status
        if user.status == "pending_verification":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email address not verified",
            )
        if user.status == "suspended":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is suspended",
            )

        # Create AuthSession
        settings = get_settings()
        auth_session = await self.session_repo.create_session(
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_days=settings.refresh_token_expire_days,
        )

        # Create RefreshToken with new family_id
        family_id = uuid.uuid4()
        raw_refresh_token = generate_secure_token(48)
        t_hash = hash_token(raw_refresh_token)
        await self.session_repo.create_refresh_token(
            session_id=auth_session.id,
            token_hash=t_hash,
            family_id=family_id,
            expires_days=settings.refresh_token_expire_days,
        )

        # Resolve active organization & permissions
        user_orgs = await self.org_repo.get_user_organizations(user.id)
        active_org: Organization | None = user_orgs[0] if user_orgs else None
        auth_session.active_organization_id = active_org.id if active_org else None
        await self.session.flush()
        active_roles: list[Role] = []
        effective_permissions: list[str] = []

        if active_org:
            membership = await self.membership_repo.get_membership(
                active_org.id, user.id
            )
            if membership and membership.status == "active":
                role_ids = [mr.role_id for mr in membership.membership_roles]
                for r_id in role_ids:
                    r = await self.role_repo.get_role_by_id(r_id)
                    if r:
                        active_roles.append(r)
                effective_permissions = await self.role_repo.get_permissions_for_roles(
                    role_ids, organization_id=active_org.id
                )

        # Create JWT access token with 10-minute lifetime
        access_token = create_access_token(
            user_id=str(user.id),
            session_id=str(auth_session.id),
            org_id=str(active_org.id) if active_org else None,
        )

        csrf_token = create_csrf_token(str(auth_session.id))

        return {
            "access_token": access_token,
            "raw_refresh_token": raw_refresh_token,
            "csrf_token": csrf_token,
            "expires_in": settings.access_token_expire_minutes * 60,
            "user": user,
            "active_organization": active_org,
            "roles": active_roles,
            "permissions": effective_permissions,
            "organizations": user_orgs,
        }

    async def rotate_refresh_token(self, raw_refresh_token: str) -> dict[str, Any]:
        """Atomic refresh token rotation with family reuse detection."""
        t_hash = hash_token(raw_refresh_token)
        token_record = await self.session_repo.get_refresh_token_by_hash(t_hash)

        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        auth_session = await self.session_repo.get_session(token_record.session_id)
        if not auth_session or auth_session.revoked_at is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been revoked or expired",
            )

        now = datetime.now(UTC)
        if (
            ensure_utc(token_record.expires_at) < now
            or ensure_utc(auth_session.expires_at) < now
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired",
            )

        # REUSE DETECTION ATTACK SCENARIO:
        # An already rotated token is a replay. Persist family revocation before
        # raising: FastAPI otherwise rolls back the request transaction.
        if token_record.rotated_at is not None:
            await self.session_repo.revoke_family_tokens(token_record.family_id)
            await self.session_repo.revoke_session(token_record.session_id)
            await self.session.commit()
            logger.warning("Refresh token replay detected; affected family revoked")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token reuse detected",
            )

        if token_record.revoked_at is not None or token_record.is_revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        # Compare-and-swap consumes the row atomically. A losing concurrent
        # request reloads the row and treats a completed rotation as replay.
        if not await self.session_repo.consume_active_refresh_token(token_record.id):
            current = await self.session_repo.get_refresh_token_by_hash(t_hash)
            if current and current.rotated_at is not None:
                await self.session_repo.revoke_family_tokens(current.family_id)
                await self.session_repo.revoke_session(current.session_id)
                await self.session.commit()
                logger.warning(
                    "Concurrent refresh token reuse detected; affected family revoked"
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token reuse detected",
            )

        # Issue new token in same family
        settings = get_settings()
        new_raw_refresh_token = generate_secure_token(48)
        new_t_hash = hash_token(new_raw_refresh_token)
        replacement = await self.session_repo.create_refresh_token(
            session_id=auth_session.id,
            token_hash=new_t_hash,
            family_id=token_record.family_id,
            expires_days=settings.refresh_token_expire_days,
        )
        await self.session_repo.link_refresh_replacement(
            token_record.id, replacement.id
        )

        user = await self.user_repo.get_by_id(auth_session.user_id)
        if not user or user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is no longer active",
            )

        # Resolve active org
        user_orgs = await self.org_repo.get_user_organizations(user.id)
        active_org = next(
            (
                org
                for org in user_orgs
                if org.id == auth_session.active_organization_id
            ),
            None,
        )
        if active_org is None and user_orgs:
            active_org = user_orgs[0]
        resolved_org_id = active_org.id if active_org else None
        if auth_session.active_organization_id != resolved_org_id:
            auth_session.active_organization_id = resolved_org_id
            await self.session.flush()

        new_access_token = create_access_token(
            user_id=str(user.id),
            session_id=str(auth_session.id),
            org_id=str(active_org.id) if active_org else None,
        )

        new_csrf_token = create_csrf_token(str(auth_session.id))

        return {
            "access_token": new_access_token,
            "raw_refresh_token": new_raw_refresh_token,
            "csrf_token": new_csrf_token,
            "expires_in": settings.access_token_expire_minutes * 60,
        }

    async def logout(
        self, session_id: uuid.UUID, raw_refresh_token: str | None = None
    ) -> None:
        """Revoke current session and refresh token."""
        await self.session_repo.revoke_session(session_id)
        if raw_refresh_token:
            t_hash = hash_token(raw_refresh_token)
            token_record = await self.session_repo.get_refresh_token_by_hash(t_hash)
            if token_record:
                await self.session_repo.revoke_refresh_token(token_record.id)

    async def logout_all(self, user_id: uuid.UUID) -> None:
        """Revoke all sessions for the given user."""
        await self.session_repo.revoke_all_user_sessions(user_id)

    async def request_password_reset(self, email: str) -> str | None:
        """Request a password reset token."""
        normalized_email = email.strip().lower()
        raw_token = generate_secure_token(32)
        t_hash = hash_token(raw_token)
        user = await self.user_repo.get_by_normalized_email(normalized_email)
        if not user:
            # Silent return to prevent email enumeration
            return None

        await self.session_repo.create_password_reset_token(
            user_id=user.id, token_hash=t_hash, expires_hours=1
        )
        return raw_token

    async def confirm_password_reset(self, token: str, new_password: str) -> None:
        """Confirm password reset and revoke all active sessions."""
        t_hash = hash_token(token)
        token_record = await self.session_repo.get_password_reset_token_by_hash(t_hash)

        if not token_record or not await self.session_repo.consume_password_reset_token(
            token_record.id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset token",
            )

        # The conditional UPDATE makes token consumption atomic across workers.

        # Update password hash
        new_hash = hash_password(new_password)
        await self.user_repo.update_password(token_record.user_id, new_hash)

        # Revoke all existing sessions for security
        await self.session_repo.revoke_all_user_sessions(token_record.user_id)
