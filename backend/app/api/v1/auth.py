from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, get_current_user, verify_origin
from app.core.config import Settings, get_settings
from app.core.dev_mail_delivery import LocalEmailDeliveryError, deliver_local_auth_email
from app.db.session import get_db
from app.schemas.auth import (
    AuthMeResponse,
    AuthMessageResponse,
    LoginRequest,
    LoginResponse,
    PasswordRecoveryRequest,
    PasswordResetRequest,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    SelectOrgRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.schemas.organization import OrganizationResponse, RoleResponse
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService
from app.services.organization_service import OrganizationService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def require_local_auth_token_delivery(
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    if not settings.is_local_mail_sink_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email delivery is not configured.",
        )


async def _capture_local_auth_message(
    request: Request,
    settings: Settings,
    recipient: str,
    purpose: str,
    token: str | None,
    lifetime_seconds: int,
) -> None:
    sink = getattr(request.app.state, "development_mail_sink", None)
    if sink is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email delivery is not configured.",
        )
    sink.capture(
        recipient=recipient,
        purpose=purpose,
        token=token,
        lifetime_seconds=lifetime_seconds,
    )

    # Keep the in-memory sink for deterministic backend tests. When local SMTP
    # is configured, deliver the same message to Mailpit for browser inspection.
    if settings.dev_mail_smtp_host:
        try:
            await deliver_local_auth_email(
                settings=settings,
                recipient=recipient,
                purpose=purpose,
                token=token,
                lifetime_seconds=lifetime_seconds,
            )
        except LocalEmailDeliveryError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "The account operation was saved, but local email delivery "
                    "failed. Check that Mailpit is running and try resending."
                ),
            ) from exc


def _enforce_auth_login_rate_limit(request: Request, email: str) -> None:
    limiter = request.app.state.auth_login_rate_limiter
    client_ip = request.client.host if request.client else "unknown"
    if not limiter.allow(client_ip, email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many sign-in attempts. Please try again later.",
        )


def _enforce_auth_recovery_rate_limit(request: Request, email: str) -> None:
    limiter = request.app.state.auth_recovery_rate_limiter
    client_ip = request.client.host if request.client else "unknown"
    if not limiter.allow(client_ip, email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="If this address is eligible, instructions will be delivered.",
        )


def _set_refresh_cookie(
    response: Response, refresh_token: str, settings: Settings
) -> None:
    response.set_cookie(
        key="sandeshvani_refresh",
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path=f"{settings.api_v1_prefix}/auth",
        max_age=settings.refresh_token_expire_days * 86400,
    )


def _clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key="sandeshvani_refresh",
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path=f"{settings.api_v1_prefix}/auth",
    )


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_origin), Depends(require_local_auth_token_delivery)],
)
async def register(
    data: RegisterRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    service = AuthService(session)
    user, verification_token = await service.register(
        email=data.email,
        password=data.password,
        full_name=data.full_name,
    )
    await session.commit()
    await _capture_local_auth_message(
        request,
        settings,
        data.email,
        "email-verification",
        verification_token,
        24 * 60 * 60,
    )
    return RegisterResponse(
        message="Registration successful. Please verify your email.",
        user_id=user.id,
    )


@router.post(
    "/verify-email",
    response_model=UserResponse,
    dependencies=[Depends(verify_origin)],
)
async def verify_email(
    data: VerifyEmailRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = AuthService(session)
    user = await service.verify_email(token=data.token)
    await session.commit()
    return user


@router.post(
    "/resend-verification",
    response_model=AuthMessageResponse,
    dependencies=[Depends(verify_origin), Depends(require_local_auth_token_delivery)],
)
async def resend_verification(
    data: ResendVerificationRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    _enforce_auth_recovery_rate_limit(request, data.email)
    service = AuthService(session)
    token = await service.resend_verification(email=data.email)
    await session.commit()
    await _capture_local_auth_message(
        request, settings, data.email, "email-verification", token, 24 * 60 * 60
    )
    return AuthMessageResponse(
        message=(
            "If this account exists and is unverified, verification instructions"
            " are available."
        )
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[Depends(verify_origin)],
)
async def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    _enforce_auth_login_rate_limit(request, data.email)
    service = AuthService(session)
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    result = await service.login(
        email=data.email,
        password=data.password,
        ip_address=ip,
        user_agent=ua,
    )
    await session.commit()

    _set_refresh_cookie(response, result["raw_refresh_token"], settings)

    return LoginResponse(
        access_token=result["access_token"],
        token_type="bearer",
        expires_in=result["expires_in"],
        csrf_token=result["csrf_token"],
        user=UserResponse.model_validate(result["user"]),
        active_organization=(
            OrganizationResponse.model_validate(result["active_organization"])
            if result["active_organization"]
            else None
        ),
        roles=[RoleResponse.model_validate(r) for r in result["roles"]],
        permissions=result["permissions"],
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(verify_origin)],
)
async def refresh_token(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    sandeshvani_refresh: Annotated[str | None, Cookie()] = None,
):
    if not sandeshvani_refresh:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)

    service = AuthService(session)
    result = await service.rotate_refresh_token(sandeshvani_refresh)
    await session.commit()

    _set_refresh_cookie(response, result["raw_refresh_token"], settings)

    return TokenResponse(
        access_token=result["access_token"],
        token_type="bearer",
        expires_in=result["expires_in"],
        csrf_token=result["csrf_token"],
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_origin)],
)
async def logout(
    response: Response,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    sandeshvani_refresh: Annotated[str | None, Cookie()] = None,
):
    service = AuthService(session)
    await service.logout(auth_ctx.session_id, sandeshvani_refresh)
    await session.commit()
    _clear_refresh_cookie(response, settings)
    return {"message": "Logged out successfully"}


@router.post(
    "/logout-all",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_origin)],
)
async def logout_all(
    response: Response,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    service = AuthService(session)
    await service.logout_all(auth_ctx.user.id)
    await session.commit()
    _clear_refresh_cookie(response, settings)
    return {"message": "All sessions have been revoked"}


@router.get(
    "/me",
    response_model=AuthMeResponse,
)
async def get_me(
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    org_service = OrganizationService(session)
    orgs = await org_service.get_user_organizations(auth_ctx.user.id)

    active_org = None
    roles: list[RoleResponse] = []
    perms: list[str] = []

    target_org_id = auth_ctx.org_id or (orgs[0].id if orgs else None)
    if target_org_id:
        membership_repo = org_service.membership_repo
        membership = await membership_repo.get_membership(
            target_org_id, auth_ctx.user.id
        )
        if membership:
            for mr in membership.membership_roles:
                r = await org_service.role_repo.get_role_by_id(mr.role_id)
                if r:
                    roles.append(RoleResponse.model_validate(r))
            perms = await org_service.role_repo.get_permissions_for_roles(
                [mr.role_id for mr in membership.membership_roles],
                organization_id=target_org_id,
            )
            active_org_record = await org_service.org_repo.get_by_id(target_org_id)
            if active_org_record:
                active_org = OrganizationResponse.model_validate(active_org_record)

    return AuthMeResponse(
        user=UserResponse.model_validate(auth_ctx.user),
        active_organization=active_org,
        organizations=[OrganizationResponse.model_validate(o) for o in orgs],
        roles=roles,
        permissions=perms,
    )


@router.post(
    "/select-org",
    dependencies=[Depends(verify_origin)],
)
async def select_org(
    data: SelectOrgRequest,
    auth_ctx: Annotated[AuthContext, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    org_service = OrganizationService(session)
    result = await org_service.switch_organization_context(
        user_id=auth_ctx.user.id,
        session_id=auth_ctx.session_id,
        target_organization_id=data.organization_id,
    )
    return {
        "access_token": result["access_token"],
        "token_type": "bearer",
        "active_organization": OrganizationResponse.model_validate(
            result["active_organization"]
        ),
        "roles": [RoleResponse.model_validate(r) for r in result["roles"]],
        "permissions": result["permissions"],
    }


@router.post(
    "/password-recovery",
    response_model=AuthMessageResponse,
    dependencies=[Depends(verify_origin), Depends(require_local_auth_token_delivery)],
)
async def password_recovery(
    data: PasswordRecoveryRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    _enforce_auth_recovery_rate_limit(request, data.email)
    service = AuthService(session)
    token = await service.request_password_reset(data.email)
    await session.commit()
    await _capture_local_auth_message(
        request, settings, data.email, "password-reset", token, 60 * 60
    )
    return AuthMessageResponse(
        message=("If this email exists, password recovery instructions are available.")
    )


@router.post(
    "/password-reset",
    dependencies=[Depends(verify_origin)],
)
async def password_reset(
    data: PasswordResetRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = AuthService(session)
    await service.confirm_password_reset(data.token, data.new_password)
    await session.commit()
    return {
        "message": (
            "Password has been reset successfully. Please log in with your new"
            " credentials."
        )
    }
