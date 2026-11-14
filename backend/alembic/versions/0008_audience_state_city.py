"""Add coordinated audience city and state-code attributes.

Revision ID: 0008_audience_state_city
Revises: 0007_auth_session_selection_login_throttle
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_audience_state_city"
down_revision: str | None = "0007_auth_session_selection_login_throttle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "audience_members",
        sa.Column("state_code", sa.String(length=2), nullable=True),
    )
    op.add_column(
        "audience_members",
        sa.Column("city", sa.String(length=120), nullable=True),
    )
    op.create_index(
        "ix_audience_members_org_state_code",
        "audience_members",
        ["organization_id", "state_code"],
    )
    op.create_index(
        "ix_audience_members_org_city",
        "audience_members",
        ["organization_id", "city"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_audience_members_org_city",
        table_name="audience_members",
    )
    op.drop_index(
        "ix_audience_members_org_state_code",
        table_name="audience_members",
    )
    op.drop_column("audience_members", "city")
    op.drop_column("audience_members", "state_code")
