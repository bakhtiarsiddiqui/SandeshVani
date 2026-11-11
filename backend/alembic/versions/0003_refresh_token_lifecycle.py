"""Add durable refresh-token rotation and revocation lifecycle fields.

Revision ID: 0003_refresh_token_lifecycle
Revises: 0002_secure_role_permissions
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_refresh_token_lifecycle"
down_revision: str | None = "0002_secure_role_permissions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("refresh_tokens", sa.Column("rotated_at", sa.DateTime(timezone=True)))
    op.add_column("refresh_tokens", sa.Column("revoked_at", sa.DateTime(timezone=True)))
    op.add_column(
        "refresh_tokens", sa.Column("replaced_by_id", sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        "fk_refresh_tokens_replaced_by",
        "refresh_tokens",
        "refresh_tokens",
        ["replaced_by_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_refresh_tokens_replaced_by", "refresh_tokens", type_="foreignkey"
    )
    op.drop_column("refresh_tokens", "replaced_by_id")
    op.drop_column("refresh_tokens", "revoked_at")
    op.drop_column("refresh_tokens", "rotated_at")
