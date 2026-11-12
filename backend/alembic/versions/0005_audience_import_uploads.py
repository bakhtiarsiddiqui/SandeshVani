"""Add tenant-scoped metadata for validated audience CSV uploads.

Revision ID: 0005_audience_import_uploads
Revises: 0004_audience_members
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_audience_import_uploads"
down_revision: str | None = "0004_audience_members"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audience_import_uploads",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("uploaded_by_id", sa.UUID(), nullable=True),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "byte_size > 0",
            name="ck_audience_import_uploads_byte_size",
        ),
        sa.CheckConstraint(
            "row_count > 0",
            name="ck_audience_import_uploads_row_count",
        ),
        sa.CheckConstraint(
            "length(sha256) = 64",
            name="ck_audience_import_uploads_sha256_length",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "id",
            name="uq_audience_import_uploads_org_id",
        ),
    )
    op.create_index(
        "ix_audience_import_uploads_org_created",
        "audience_import_uploads",
        ["organization_id", "created_at"],
        unique=False,
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE audience_import_uploads ENABLE ROW LEVEL SECURITY;")
        op.execute("ALTER TABLE audience_import_uploads FORCE ROW LEVEL SECURITY;")
        op.execute(
            """
            CREATE POLICY tenant_isolation ON audience_import_uploads
            USING (
                organization_id = NULLIF(
                    current_setting('app.current_org', true), ''
                )::uuid
            )
            WITH CHECK (
                organization_id = NULLIF(
                    current_setting('app.current_org', true), ''
                )::uuid
            );
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS tenant_isolation ON audience_import_uploads;")
        op.execute("ALTER TABLE audience_import_uploads DISABLE ROW LEVEL SECURITY;")

    op.drop_index(
        "ix_audience_import_uploads_org_created",
        table_name="audience_import_uploads",
    )
    op.drop_table("audience_import_uploads")
