import os
from collections.abc import AsyncGenerator

# Importing app.main constructs the application. Keep the test process explicitly
# local so production's intentional fail-fast validation remains testable.
os.environ.setdefault("APP_ENV", "local")
os.environ.setdefault("DEPLOYMENT_ENVIRONMENT", "development")

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.main import create_app
from app.models.base import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_SETTINGS = Settings(
    _env_file=None,
    app_env="local",
    deployment_environment="development",
    enable_local_mail_sink=True,
)
app = create_app(TEST_SETTINGS)
app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS


@pytest.fixture
def test_app():
    """Expose the exact FastAPI instance used by the shared test clients."""
    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def development_mail_sink():
    sink = app.state.development_mail_sink
    sink.clear()
    return sink


@pytest.fixture
def auth_recovery_rate_limiter():
    limiter = app.state.auth_recovery_rate_limiter
    limiter.clear()
    return limiter


@pytest.fixture
def auth_login_rate_limiter():
    limiter = app.state.auth_login_rate_limiter
    limiter.clear()
    return limiter


@pytest.fixture
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def async_client(
    test_db_session: AsyncSession,
    development_mail_sink,
    auth_recovery_rate_limiter,
    auth_login_rate_limiter,
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Origin": "http://localhost:5173"},
    ) as client:
        yield client

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
