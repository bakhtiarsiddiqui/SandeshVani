import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class OutboxEvent(Base, UUIDPrimaryKeyMixin):
    """Tenant-scoped durable message awaiting publication to Celery/Redis."""

    __tablename__ = "outbox_events"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'publishing', 'published', 'dead_letter')",
            name="ck_outbox_events_status",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_outbox_events_attempt_count",
        ),
        ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "organization_id",
            "id",
            name="uq_outbox_events_org_id",
        ),
        UniqueConstraint(
            "organization_id",
            "aggregate_type",
            "aggregate_id",
            "event_type",
            name="uq_outbox_events_aggregate_event",
        ),
        Index(
            "ix_outbox_events_dispatch",
            "organization_id",
            "status",
            "available_at",
            "locked_until",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(24),
        default="pending",
        nullable=False,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
