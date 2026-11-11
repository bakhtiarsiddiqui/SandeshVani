from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str
    version: str


@router.get("", response_model=HealthResponse)
def get_health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        app=settings.app_name,
        environment=settings.app_env,
        version=settings.version,
    )
