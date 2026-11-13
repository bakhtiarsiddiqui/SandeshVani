from fastapi import APIRouter

from app.api.v1.audiences import router as audiences_router
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.governance import router as governance_router
from app.api.v1.organizations import router as organizations_router
from app.core.config import Settings, get_settings


def create_api_v1_router(settings: Settings | None = None) -> APIRouter:
    settings = settings or get_settings()
    router = APIRouter(prefix=settings.api_v1_prefix)
    router.include_router(health_router)
    router.include_router(auth_router)
    router.include_router(organizations_router)
    router.include_router(audiences_router)
    router.include_router(governance_router)
    return router
