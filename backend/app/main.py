from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import create_api_v1_router
from app.core.config import Settings, get_settings
from app.core.dev_mail import DevelopmentMailSink
from app.core.rate_limit import AuthRecoveryRateLimiter


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.version,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        docs_url=f"{settings.api_v1_prefix}/docs",
        redoc_url=f"{settings.api_v1_prefix}/redoc",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-CSRF-Token",
            "X-Organization-ID",
        ],
        expose_headers=["X-CSRF-Token"],
    )

    application.state.development_mail_sink = (
        DevelopmentMailSink() if settings.is_local_mail_sink_enabled else None
    )
    application.state.auth_recovery_rate_limiter = AuthRecoveryRateLimiter(
        email_limit=settings.auth_recovery_email_limit,
        ip_limit=settings.auth_recovery_ip_limit,
        window_seconds=settings.auth_recovery_rate_window_seconds,
    )

    application.include_router(create_api_v1_router(settings))

    @application.get("/", tags=["Root"])
    def root() -> dict[str, str]:
        return {
            "message": (
                "SandeshVani API is operational. Visit /api/v1/health "
                "for service status."
            )
        }

    return application


app = create_app()
