"""Create tenant-scoped audience contact records.

Revision ID: 0004_audience_members
Revises: 0003_refresh_token_lifecycle
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_audience_members"
down_revision: str | None = "0003_refresh_token_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audience_members",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("phone", sa.String(length=16), nullable=True),
        sa.Column(
            "preferred_language",
            sa.String(length=12),
            server_default="en",
            nullable=False,
        ),
        sa.Column("district", sa.String(length=150), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="active",
            nullable=False,
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(trim(full_name)) > 0",
            name="ck_audience_members_full_name",
        ),
        sa.CheckConstraint(
            "email IS NOT NULL OR phone IS NOT NULL",
            name="ck_audience_members_contact_point",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_audience_members_status",
        ),
        sa.CheckConstraint(
            "preferred_language IN ('en', 'hi')",
            name="ck_audience_members_language",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "id", name="uq_audience_members_org_id"
        ),
    )

    op.create_index(
        "ix_audience_members_organization_id",
        "audience_members",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_audience_members_status",
        "audience_members",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_audience_members_org_created",
        "audience_members",
        ["organization_id", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_audience_members_org_status",
        "audience_members",
        ["organization_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_audience_members_org_district",
        "audience_members",
        ["organization_id", "district"],
        unique=False,
    )
    op.create_index(
        "ix_audience_members_org_language",
        "audience_members",
        ["organization_id", "preferred_language"],
        unique=False,
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE audience_members ENABLE ROW LEVEL SECURITY;")
        op.execute("ALTER TABLE audience_members FORCE ROW LEVEL SECURITY;")
        op.execute(
            """
            CREATE POLICY tenant_isolation ON audience_members
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
        op.execute("DROP POLICY IF EXISTS tenant_isolation ON audience_members;")
        op.execute("ALTER TABLE audience_members DISABLE ROW LEVEL SECURITY;")

    op.drop_index("ix_audience_members_org_language", table_name="audience_members")
    op.drop_index("ix_audience_members_org_district", table_name="audience_members")
    op.drop_index("ix_audience_members_org_status", table_name="audience_members")
    op.drop_index("ix_audience_members_org_created", table_name="audience_members")
    op.drop_index("ix_audience_members_status", table_name="audience_members")
    op.drop_index(
        "ix_audience_members_organization_id",
        table_name="audience_members",
    )
    op.drop_table("audience_members")
