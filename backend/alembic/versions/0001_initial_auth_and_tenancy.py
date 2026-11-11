"""Initial auth and tenancy migration with RLS.

Revision ID: 0001_initial_auth_and_tenancy
Revises:
Create Date: 2026-11-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial_auth_and_tenancy"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("normalized_email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="pending_verification",
        ),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_users_normalized_email"),
        "users",
        ["normalized_email"],
        unique=True,
    )
    op.create_index(op.f("ix_users_status"), "users", ["status"], unique=False)

    # 2. organizations
    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="active",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_organizations_slug"), "organizations", ["slug"], unique=True
    )
    op.create_index(
        op.f("ix_organizations_status"),
        "organizations",
        ["status"],
        unique=False,
    )

    # 3. memberships
    op.create_table(
        "memberships",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="active",
        ),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "user_id", name="uq_memberships_org_user"
        ),
        sa.UniqueConstraint("organization_id", "id", name="uq_memberships_org_id"),
    )
    op.create_index(
        op.f("ix_memberships_organization_id"),
        "memberships",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_memberships_user_id"), "memberships", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_memberships_status"), "memberships", ["status"], unique=False
    )

    # 4. permissions
    op.create_table(
        "permissions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_permissions_code"), "permissions", ["code"], unique=True)

    # 5. roles
    op.create_table(
        "roles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=True),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column(
            "is_system_role",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(scope = 'organization' AND organization_id IS NOT NULL) OR "
            "(scope = 'platform' AND organization_id IS NULL)",
            name="ck_roles_scope_org_id",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "id", name="uq_roles_org_id"),
        sa.UniqueConstraint("scope", "id", name="uq_roles_scope_id"),
    )
    op.create_index(
        op.f("ix_roles_organization_id"),
        "roles",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "uq_roles_org_name_ci",
        "roles",
        ["organization_id", sa.text("lower(name)")],
        unique=True,
        postgresql_where=sa.text("scope = 'organization'"),
        sqlite_where=sa.text("scope = 'organization'"),
    )
    op.create_index(
        "uq_roles_platform_name_ci",
        "roles",
        [sa.text("lower(name)")],
        unique=True,
        postgresql_where=sa.text("scope = 'platform'"),
        sqlite_where=sa.text("scope = 'platform'"),
    )

    # 6. role_permissions
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("permission_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["permission_id"], ["permissions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )

    # 7. membership_roles (composite tenant foreign key)
    op.create_table(
        "membership_roles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("membership_id", sa.UUID(), nullable=False),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("assigned_by", sa.UUID(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["organization_id", "membership_id"],
            ["memberships.organization_id", "memberships.id"],
            name="fk_membership_roles_composite_org_membership",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "role_id"],
            ["roles.organization_id", "roles.id"],
            name="fk_membership_roles_composite_org_role",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "membership_id", "role_id", name="uq_membership_roles_member_role"
        ),
    )
    op.create_index(
        op.f("ix_membership_roles_organization_id"),
        "membership_roles",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_membership_roles_membership_id"),
        "membership_roles",
        ["membership_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_membership_roles_role_id"),
        "membership_roles",
        ["role_id"],
        unique=False,
    )

    # 8. platform_role_assignments
    op.create_table(
        "platform_role_assignments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "role_scope",
            sa.String(length=20),
            nullable=False,
            server_default="platform",
        ),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("assigned_by", sa.UUID(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "role_scope = 'platform'",
            name="ck_platform_role_assignments_role_scope",
        ),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["role_scope", "role_id"],
            ["roles.scope", "roles.id"],
            name="fk_platform_role_assignments_composite_scope_role",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role_id", name="uq_platform_roles_user_role"),
    )
    op.create_index(
        op.f("ix_platform_role_assignments_user_id"),
        "platform_role_assignments",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_platform_role_assignments_role_id"),
        "platform_role_assignments",
        ["role_id"],
        unique=False,
    )

    # 9. auth_sessions
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("ip_address", sa.String(length=100), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_auth_sessions_user_id"),
        "auth_sessions",
        ["user_id"],
        unique=False,
    )

    # 10. refresh_tokens
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("family_id", sa.UUID(), nullable=False),
        sa.Column(
            "is_revoked",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"], ["auth_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_refresh_tokens_family_id"),
        "refresh_tokens",
        ["family_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_refresh_tokens_session_id"),
        "refresh_tokens",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_refresh_tokens_token_hash"),
        "refresh_tokens",
        ["token_hash"],
        unique=True,
    )

    # 11. email_verification_tokens
    op.create_table(
        "email_verification_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_email_verification_tokens_token_hash"),
        "email_verification_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_email_verification_tokens_user_id"),
        "email_verification_tokens",
        ["user_id"],
        unique=False,
    )

    # 12. password_reset_tokens
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_password_reset_tokens_token_hash"),
        "password_reset_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_password_reset_tokens_user_id"),
        "password_reset_tokens",
        ["user_id"],
        unique=False,
    )

    # 13. PostgreSQL Row Level Security (RLS) policies for tenant-owned tables
    #
    # FORCE ROW LEVEL SECURITY is required because the application database
    # role (sandeshvani_app) currently owns the tables it creates through
    # Alembic.  Without FORCE, the table owner bypasses all RLS policies
    # regardless of whether it has BYPASSRLS.  AGENTS.md mandates that the
    # application role must not bypass RLS, so FORCE is essential until a
    # separate migration-owner role is introduced.
    #
    # When app.current_org is unset (empty string or NULL),
    #   NULLIF(current_setting('app.current_org', true), '')::uuid
    # evaluates to NULL, and  organization_id = NULL  is always false,
    # so no organization-scoped rows are visible without an explicit tenant
    # context.  This is the intended safe default.

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # -- memberships --------------------------------------------------
        op.execute("ALTER TABLE memberships ENABLE ROW LEVEL SECURITY;")
        op.execute("ALTER TABLE memberships FORCE ROW LEVEL SECURITY;")
        op.execute(
            """
            CREATE POLICY tenant_isolation ON memberships
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

        # -- membership_roles ---------------------------------------------
        op.execute("ALTER TABLE membership_roles ENABLE ROW LEVEL SECURITY;")
        op.execute("ALTER TABLE membership_roles FORCE ROW LEVEL SECURITY;")
        op.execute(
            """
            CREATE POLICY tenant_isolation ON membership_roles
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

        # -- roles --------------------------------------------------------
        # The roles table contains both platform-scoped rows
        # (organization_id IS NULL) and organization-scoped rows.
        # Separate per-command policies enforce:
        #   SELECT : platform roles always visible; org roles only to tenant.
        #   INSERT : only organization-scoped rows for the active tenant.
        #   UPDATE : only organization-scoped rows for the active tenant.
        #   DELETE : only organization-scoped rows for the active tenant.
        # The INSERT/UPDATE/DELETE policies intentionally exclude
        # platform roles, so the ordinary application role cannot create
        # or modify them.  Platform role management requires a privileged
        # role or a dedicated admin pathway added in a later release.

        op.execute("ALTER TABLE roles ENABLE ROW LEVEL SECURITY;")
        op.execute("ALTER TABLE roles FORCE ROW LEVEL SECURITY;")

        # SELECT: platform roles (org_id IS NULL) always visible;
        #         org roles visible only when tenant context matches.
        op.execute(
            """
            CREATE POLICY roles_select ON roles
            FOR SELECT
            USING (
                organization_id IS NULL
                OR organization_id = NULLIF(
                    current_setting('app.current_org', true), ''
                )::uuid
            );
            """
        )

        # INSERT: only organization-scoped roles for the active tenant.
        op.execute(
            """
            CREATE POLICY roles_insert ON roles
            FOR INSERT
            WITH CHECK (
                scope = 'organization'
                AND organization_id IS NOT NULL
                AND organization_id = NULLIF(
                    current_setting('app.current_org', true), ''
                )::uuid
            );
            """
        )

        # UPDATE: only organization-scoped roles for the active tenant.
        # USING filters which existing rows can be updated;
        # WITH CHECK validates the new row values after the update.
        op.execute(
            """
            CREATE POLICY roles_update ON roles
            FOR UPDATE
            USING (
                scope = 'organization'
                AND organization_id IS NOT NULL
                AND organization_id = NULLIF(
                    current_setting('app.current_org', true), ''
                )::uuid
            )
            WITH CHECK (
                scope = 'organization'
                AND organization_id IS NOT NULL
                AND organization_id = NULLIF(
                    current_setting('app.current_org', true), ''
                )::uuid
            );
            """
        )

        # DELETE: only organization-scoped roles for the active tenant.
        op.execute(
            """
            CREATE POLICY roles_delete ON roles
            FOR DELETE
            USING (
                scope = 'organization'
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
        # roles RLS (reverse order of creation)
        op.execute("DROP POLICY IF EXISTS roles_delete ON roles;")
        op.execute("DROP POLICY IF EXISTS roles_update ON roles;")
        op.execute("DROP POLICY IF EXISTS roles_insert ON roles;")
        op.execute("DROP POLICY IF EXISTS roles_select ON roles;")
        op.execute("ALTER TABLE roles DISABLE ROW LEVEL SECURITY;")

        # membership_roles RLS
        op.execute("DROP POLICY IF EXISTS tenant_isolation ON membership_roles;")
        op.execute("ALTER TABLE membership_roles DISABLE ROW LEVEL SECURITY;")

        # memberships RLS
        op.execute("DROP POLICY IF EXISTS tenant_isolation ON memberships;")
        op.execute("ALTER TABLE memberships DISABLE ROW LEVEL SECURITY;")

    op.drop_table("password_reset_tokens")
    op.drop_table("email_verification_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("auth_sessions")
    op.drop_table("platform_role_assignments")
    op.drop_table("membership_roles")
    op.drop_table("role_permissions")
    op.drop_index("uq_roles_platform_name_ci", table_name="roles")
    op.drop_index("uq_roles_org_name_ci", table_name="roles")
    op.drop_table("roles")
    op.drop_table("permissions")
    op.drop_table("memberships")
    op.drop_table("organizations")
    op.drop_table("users")
