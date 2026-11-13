"""Persist selected organization and failed-login windows.

Revision ID: 0007_auth_session_selection_login_throttle
Revises: 0006_audience_import_jobs
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_auth_session_selection_login_throttle"
down_revision: str | None = "0006_audience_import_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "auth_sessions",
        sa.Column("selected_organization_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_auth_sessions_selected_organization",
        "auth_sessions",
        "organizations",
        ["selected_organization_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_auth_sessions_selected_organization_id",
        "auth_sessions",
        ["selected_organization_id"],
    )

    op.create_table(
        "auth_login_attempt_windows",
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "attempt_count > 0",
            name="ck_login_attempt_count_positive",
        ),
        sa.PrimaryKeyConstraint("key_hash"),
    )
    op.create_index(
        "ix_auth_login_attempt_windows_window_started_at",
        "auth_login_attempt_windows",
        ["window_started_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_auth_login_attempt_windows_window_started_at",
        table_name="auth_login_attempt_windows",
    )
    op.drop_table("auth_login_attempt_windows")
    op.drop_index(
        "ix_auth_sessions_selected_organization_id",
        table_name="auth_sessions",
    )
    op.drop_constraint(
        "fk_auth_sessions_selected_organization",
        "auth_sessions",
        type_="foreignkey",
    )
    op.drop_column("auth_sessions", "selected_organization_id")
