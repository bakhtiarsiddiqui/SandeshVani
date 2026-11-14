from collections.abc import Callable
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker


def create_sync_session_factory(
    database_url: str,
) -> tuple[Any, Callable[[], Session]]:
    """Create a synchronous SQLAlchemy engine/session factory for Celery workers.

    The API continues to use its async driver. Celery tasks use psycopg2 so a
    worker does not reuse asyncpg connections across per-task event loops.
    """
    url = make_url(database_url)
    if url.drivername == "postgresql+asyncpg":
        url = url.set(drivername="postgresql+psycopg2")
    elif url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg2")

    engine = create_engine(
        url,
        pool_pre_ping=True,
        future=True,
    )
    factory = sessionmaker(
        bind=engine,
        class_=Session,
        expire_on_commit=False,
        autoflush=False,
    )
    return engine, factory
