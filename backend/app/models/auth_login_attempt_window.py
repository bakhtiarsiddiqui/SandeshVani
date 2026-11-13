from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuthLoginAttemptWindow(Base):
    """HMAC-keyed, time-bounded failed-login counters (no raw identifiers)."""

    __tablename__ = "auth_login_attempt_windows"
    __table_args__ = (
        CheckConstraint("attempt_count > 0", name="ck_login_attempt_count_positive"),
    )

    key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False)
    window_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
