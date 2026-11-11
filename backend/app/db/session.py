import uuid
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        db_url = settings.get_database_url()
        _engine = create_async_engine(
            db_url,
            echo=False,
            future=True,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_factory


async def set_tenant_context(session: AsyncSession, organization_id: uuid.UUID) -> None:
    """Set the transaction-local PostgreSQL tenant context.

    Uses `set_config('app.current_org', :org_id, true)` where `true` ensures
    the context is scoped to the current transaction only and does not leak
    across pooled connections.
    """
    bind = session.bind or get_engine()
    dialect_name = bind.dialect.name

    session.info["current_org"] = organization_id
    if dialect_name == "postgresql":
        await session.execute(
            text("SELECT set_config('app.current_org', :org_id, true)"),
            {"org_id": str(organization_id)},
        )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async database session per request."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()
