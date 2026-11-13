"""Persist the active organization per session and add audience location.

Revision ID: 0008_session_org_audience_location
Revises: 0007_audience_identity
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_session_org_audience_location"
down_revision: str | None = "0007_audience_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "auth_sessions",
        sa.Column("active_organization_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_auth_sessions_active_organization",
        "auth_sessions",
        "organizations",
        ["active_organization_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_auth_sessions_active_organization_id",
        "auth_sessions",
        ["active_organization_id"],
        unique=False,
    )

    op.add_column(
        "audience_members",
        sa.Column("state_code", sa.String(length=8), nullable=True),
    )
    op.add_column(
        "audience_members",
        sa.Column("city", sa.String(length=150), nullable=True),
    )
    op.create_index(
        "ix_audience_members_org_state",
        "audience_members",
        ["organization_id", "state_code"],
        unique=False,
    )
    op.create_index(
        "ix_audience_members_org_city",
        "audience_members",
        ["organization_id", "city"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_audience_members_org_city", table_name="audience_members")
    op.drop_index("ix_audience_members_org_state", table_name="audience_members")
    op.drop_column("audience_members", "city")
    op.drop_column("audience_members", "state_code")

    op.drop_index(
        "ix_auth_sessions_active_organization_id",
        table_name="auth_sessions",
    )
    op.drop_constraint(
        "fk_auth_sessions_active_organization",
        "auth_sessions",
        type_="foreignkey",
    )
    op.drop_column("auth_sessions", "active_organization_id")
