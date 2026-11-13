from collections.abc import Callable
from datetime import UTC, datetime
import uuid
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    ensure_utc,
    verify_access_token,
    verify_csrf_token,
)
from app.db.session import get_db, set_tenant_context
from app.models.membership import Membership
from app.models.organization import Organization
from app.models.user import User
from app.repositories.membership_repo import MembershipRepository
from app.repositories.organization_repo import OrganizationRepository
from app.repositories.role_repo import RoleRepository
from app.repositories.session_repo import SessionRepository
from app.repositories.user_repo import UserRepository

security_bearer = HTTPBearer(auto_error=False)


class AuthContext:
    def __init__(
        self,
        user: User,
        session_id: uuid.UUID,
        org_id: uuid.UUID | None = None,
    ):
        self.user = user
        self.session_id = session_id
        self.org_id = org_id


class TenantContext:
    def __init__(
        self,
        organization: Organization,
        membership: Membership,
        permissions: list[str],
    ):
        self.organization = organization
        self.membership = membership
        self.permissions = permissions


async def get_current_user(
    auth: Annotated[HTTPAuthorizationCredentials | None, Depends(security_bearer)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AuthContext:
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = verify_access_token(auth.credentials)
    except PyJWTError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err

    user_id_str = payload.get("sub")
    session_id_str = payload.get("session_id")
    org_id_str = payload.get("org_id")

    if not user_id_str or not session_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = uuid.UUID(user_id_str)
    session_id = uuid.UUID(session_id_str)
    org_id = uuid.UUID(org_id_str) if org_id_str else None

    # Check active session in DB
    session_repo = SessionRepository(session)
    auth_session = await session_repo.get_session(session_id)
    if (
        not auth_session
        or auth_session.revoked_at is not None
        or ensure_utc(auth_session.expires_at) <= datetime.now(UTC)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked or expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive or suspended",
        )

    return AuthContext(user=user, session_id=session_id, org_id=org_id)


async def get_tenant_context(
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    x_organization_id: Annotated[str | None, Header()] = None,
) -> TenantContext:
    target_org_id = None
    if x_organization_id:
        try:
            target_org_id = uuid.UUID(x_organization_id)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-Organization-ID header format",
            ) from err
    elif auth_ctx.org_id:
        target_org_id = auth_ctx.org_id

    if not target_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No organization context selected. Provide X-Organization-ID"
                " or authenticate within an organization."
            ),
        )

    # Establish transaction-local PostgreSQL tenant context before querying
    # tenant-protected membership records (so RLS allows reading this org's data)
    await set_tenant_context(session, target_org_id)

    # Verify user's active membership (never treat header as proof of membership)
    membership_repo = MembershipRepository(session)
    membership = await membership_repo.get_membership(target_org_id, auth_ctx.user.id)
    if not membership or membership.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an active member of this organization",
        )

    org_repo = OrganizationRepository(session)
    organization = await org_repo.get_by_id(target_org_id)
    if not organization or organization.status != "active":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or inactive",
        )

    # Resolve effective permissions
    role_repo = RoleRepository(session)
    role_ids = [mr.role_id for mr in membership.membership_roles]
    permissions = await role_repo.get_permissions_for_roles(
        role_ids, organization_id=target_org_id
    )

    return TenantContext(
        organization=organization,
        membership=membership,
        permissions=permissions,
    )


def require_permissions(*required_permissions: str) -> Callable:
    def check_permissions(
        request: Request,
        tenant_ctx: Annotated[TenantContext, Depends(get_tenant_context)],
    ) -> TenantContext:
        path_org_id_val = request.path_params.get("organization_id")
        if path_org_id_val is not None:
            try:
                path_org_id = (
                    path_org_id_val
                    if isinstance(path_org_id_val, uuid.UUID)
                    else uuid.UUID(str(path_org_id_val))
                )
            except ValueError as err:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid organization ID format in path",
                ) from err

            if path_org_id != tenant_ctx.organization.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Organization path ID does not match active tenant context",
                )

        user_perms = set(tenant_ctx.permissions)
        missing = [p for p in required_permissions if p not in user_perms]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required permission missing: {', '.join(missing)}",
            )
        return tenant_ctx

    return check_permissions


def verify_csrf(
    request: Request,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    x_csrf_token: Annotated[str | None, Header()] = None,
) -> None:
    """CSRF verification for state-changing operations."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    if not x_csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing CSRF token in X-CSRF-Token header",
        )

    if not verify_csrf_token(x_csrf_token, str(auth_ctx.session_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired CSRF token",
        )


def verify_origin(request: Request) -> None:
    """Origin validation for state-changing requests."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    origin = request.headers.get("origin")
    referer = request.headers.get("referer")

    settings = get_settings()
    allowed = set(settings.allowed_origins)

    if origin:
        if origin not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden cross-origin request",
            )
    elif referer:
        parsed = urlsplit(referer)
        referer_origin = f"{parsed.scheme}://{parsed.netloc}"
        if referer_origin not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden cross-origin referer",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Origin or Referer header is required for state-changing requests",
        )
