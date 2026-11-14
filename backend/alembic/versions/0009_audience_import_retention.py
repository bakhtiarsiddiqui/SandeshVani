"""Add retention metadata for private audience import files.

Revision ID: 0009_audience_import_retention
Revises: 0008_audience_state_city
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_audience_import_retention"
down_revision: str | None = "0008_audience_state_city"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "audience_import_uploads",
        sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "audience_import_uploads",
        sa.Column("file_deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Existing source files get a conservative 30-day retention interval from
    # their original upload timestamp; no historical metadata is discarded.
    op.execute(
        sa.text(
            "UPDATE audience_import_uploads "
            "SET retention_expires_at = created_at + INTERVAL '30 days' "
            "WHERE retention_expires_at IS NULL"
        )
    )
    op.alter_column(
        "audience_import_uploads",
        "retention_expires_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )
    op.create_index(
        "ix_audience_import_uploads_org_retention",
        "audience_import_uploads",
        ["organization_id", "retention_expires_at", "file_deleted_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_audience_import_uploads_org_retention",
        table_name="audience_import_uploads",
    )
    op.drop_column("audience_import_uploads", "file_deleted_at")
    op.drop_column("audience_import_uploads", "retention_expires_at")
