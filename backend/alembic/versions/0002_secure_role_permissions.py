"""Secure role_permissions with tenant-scoping, composite FKs, and RLS.

Revision ID: 0002_secure_role_permissions
Revises: 0001_initial_auth_and_tenancy
Create Date: 2026-11-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_secure_role_permissions"
down_revision: str | None = "0001_initial_auth_and_tenancy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add role_scope and organization_id columns to role_permissions
    # role_scope is initially nullable to allow data backfill
    op.add_column(
        "role_permissions",
        sa.Column("role_scope", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "role_permissions",
        sa.Column("organization_id", sa.UUID(), nullable=True),
    )

    # 2. Backfill both columns from the referenced roles rows
    op.execute(
        """
        UPDATE role_permissions
        SET role_scope = (
                SELECT scope FROM roles WHERE roles.id = role_permissions.role_id
            ),
            organization_id = (
                SELECT organization_id FROM roles
                WHERE roles.id = role_permissions.role_id
            );
        """
    )

    # 3. Fail clearly if an existing association cannot be matched to exactly one role
    bind = op.get_bind()
    unmatched_count = bind.execute(
        sa.text("SELECT count(*) FROM role_permissions WHERE role_scope IS NULL")
    ).scalar()
    if unmatched_count and unmatched_count > 0:
        raise ValueError(
            f"Migration failed: {unmatched_count} role_permissions rows "
            "could not be matched to an existing role"
        )

    # 4. Alter role_scope to non-null now that backfill is verified
    op.alter_column(
        "role_permissions",
        "role_scope",
        existing_type=sa.String(length=20),
        nullable=False,
    )

    # 5. Index on organization_id for fast tenant filtering
    op.create_index(
        op.f("ix_role_permissions_organization_id"),
        "role_permissions",
        ["organization_id"],
        unique=False,
    )

    # 6. Add check constraint enforcing valid scope and organization_id relationship
    op.create_check_constraint(
        "ck_role_permissions_scope_org_id",
        "role_permissions",
        "(role_scope = 'organization' AND organization_id IS NOT NULL) OR "
        "(role_scope = 'platform' AND organization_id IS NULL)",
    )

    # 7. Add composite foreign keys matching (organization_id, id) and (scope, id)
    op.create_foreign_key(
        "fk_role_permissions_composite_org_role",
        "role_permissions",
        "roles",
        ["organization_id", "role_id"],
        ["organization_id", "id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_role_permissions_composite_scope_role",
        "role_permissions",
        "roles",
        ["role_scope", "role_id"],
        ["scope", "id"],
        ondelete="CASCADE",
    )

    # 8. PostgreSQL Row Level Security (RLS) policies for role_permissions
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE role_permissions ENABLE ROW LEVEL SECURITY;")
        op.execute("ALTER TABLE role_permissions FORCE ROW LEVEL SECURITY;")

        # SELECT: platform grants (org_id IS NULL) are readable;
        #         org grants are readable only for the active tenant.
        op.execute(
            """
            CREATE POLICY role_permissions_select ON role_permissions
            FOR SELECT
            USING (
                organization_id IS NULL
                OR organization_id = NULLIF(
                    current_setting('app.current_org', true), ''
                )::uuid
            );
            """
        )

        # INSERT: only organization-scoped grants for the active tenant.
        # Platform grants are denied.
        op.execute(
            """
            CREATE POLICY role_permissions_insert ON role_permissions
            FOR INSERT
            WITH CHECK (
                role_scope = 'organization'
                AND organization_id IS NOT NULL
                AND organization_id = NULLIF(
                    current_setting('app.current_org', true), ''
                )::uuid
            );
            """
        )

        # UPDATE: only organization-scoped grants for the active tenant.
        # Platform grants are denied.
        op.execute(
            """
            CREATE POLICY role_permissions_update ON role_permissions
            FOR UPDATE
            USING (
                role_scope = 'organization'
                AND organization_id IS NOT NULL
                AND organization_id = NULLIF(
                    current_setting('app.current_org', true), ''
                )::uuid
            )
            WITH CHECK (
                role_scope = 'organization'
                AND organization_id IS NOT NULL
                AND organization_id = NULLIF(
                    current_setting('app.current_org', true), ''
                )::uuid
            );
            """
        )

        # DELETE: only organization-scoped grants for the active tenant.
        # Platform grants are denied.
        op.execute(
            """
            CREATE POLICY role_permissions_delete ON role_permissions
            FOR DELETE
            USING (
                role_scope = 'organization'
                AND organization_id IS NOT NULL
                AND organization_id = NULLIF(
                    current_setting('app.current_org', true), ''
                )::uuid
            );
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS role_permissions_delete ON role_permissions;")
        op.execute("DROP POLICY IF EXISTS role_permissions_update ON role_permissions;")
        op.execute("DROP POLICY IF EXISTS role_permissions_insert ON role_permissions;")
        op.execute("DROP POLICY IF EXISTS role_permissions_select ON role_permissions;")
        op.execute("ALTER TABLE role_permissions DISABLE ROW LEVEL SECURITY;")

    op.drop_constraint(
        "fk_role_permissions_composite_scope_role",
        "role_permissions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_role_permissions_composite_org_role",
        "role_permissions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "ck_role_permissions_scope_org_id",
        "role_permissions",
        type_="check",
    )
    op.drop_index(
        op.f("ix_role_permissions_organization_id"),
        table_name="role_permissions",
    )
    op.drop_column("role_permissions", "organization_id")
    op.drop_column("role_permissions", "role_scope")
