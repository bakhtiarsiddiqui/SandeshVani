"""PostgreSQL integration tests for roles RLS policies.

These tests require a real PostgreSQL instance and CANNOT run on SQLite.
They validate:
  1. Platform roles are readable without tenant context.
  2. Organization roles are inaccessible without tenant context.
  3. Organization A cannot read organization B's roles.
  4. Organization A cannot INSERT/UPDATE/DELETE organization B's roles.
  5. The ordinary application role cannot create platform roles.
  6. FORCE ROW LEVEL SECURITY is enforced for table owners.
  7. Application and owner roles have no superuser or BYPASSRLS privileges.
  8. Application role does not own protected tables.
  9. The migration can be upgraded and downgraded cleanly.

Prerequisites
-------------
Set the environment variable ``SANDESHVANI_PG_TEST_URL`` to a PostgreSQL
connection string for a **superuser** or **createdb** role:

    export SANDESHVANI_PG_TEST_URL="postgresql://postgres:secret@localhost:5432/postgres"

The tests create a disposable database ``sandeshvani_rls_test``, a disposable
owner role ``sandeshvani_rls_testowner``, and a restricted application role
``sandeshvani_rls_testapp``, then tear them down after the run.
They never touch the main development database.

Run with:

    SANDESHVANI_PG_TEST_URL="postgresql://user:pass@localhost:5432/postgres" \\
        PYTHONPATH=backend pytest -c backend/pyproject.toml \\
        backend/tests/test_rls_integration.py -v
"""

from __future__ import annotations

import os
import uuid
from urllib.parse import urlsplit, urlunsplit

import pytest

# Skip the entire module if asyncpg is missing or no PG URL is provided
asyncpg = pytest.importorskip("asyncpg", reason="asyncpg required for PG integration")

PG_TEST_URL = os.environ.get("SANDESHVANI_PG_TEST_URL", "")
if not PG_TEST_URL:
    pytest.skip(
        "SANDESHVANI_PG_TEST_URL not set — skipping PostgreSQL integration tests",
        allow_module_level=True,
    )

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TEST_DB = "sandeshvani_rls_test"
APP_ROLE = "sandeshvani_rls_testapp"
APP_ROLE_PASSWORD = "test_app_pw_change_me"
OWNER_ROLE = "sandeshvani_rls_testowner"
OWNER_ROLE_PASSWORD = "test_owner_pw_change_me"


# ---------------------------------------------------------------------------
# Helpers — parse asyncpg DSN components
# ---------------------------------------------------------------------------
def _build_dsn(base_url: str, user: str, password: str, dbname: str) -> str:
    """Build a postgresql:// URL with specific credentials and database name."""
    parsed = urlsplit(base_url)
    host_port = parsed.netloc.split("@")[-1]
    new_netloc = f"{user}:{password}@{host_port}"
    return urlunsplit(
        (parsed.scheme, new_netloc, f"/{dbname}", parsed.query, parsed.fragment)
    )


def _admin_dsn(base_url: str, dbname: str) -> str:
    """Build an admin postgresql:// URL pointing to dbname with same credentials."""
    parsed = urlsplit(base_url)
    return urlunsplit(
        (parsed.scheme, parsed.netloc, f"/{dbname}", parsed.query, parsed.fragment)
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def pg_setup():
    """Create disposable test database, owner role, app role, schema, and RLS.

    Yields a dict with connection details, then tears down all test resources.
    """
    # Connect as superuser to the maintenance database
    admin_conn = await asyncpg.connect(PG_TEST_URL)

    try:
        # Terminate any stale connections to the test DB
        await admin_conn.execute(
            f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{TEST_DB}' AND pid <> pg_backend_pid();
            """
        )

        # Drop pre-existing test database and roles (idempotent cleanup)
        await admin_conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB};")
        await admin_conn.execute(f"DROP ROLE IF EXISTS {APP_ROLE};")
        await admin_conn.execute(f"DROP ROLE IF EXISTS {OWNER_ROLE};")

        # Create non-superuser, non-bypassrls table owner role
        await admin_conn.execute(
            f"""
            CREATE ROLE {OWNER_ROLE}
            LOGIN PASSWORD '{OWNER_ROLE_PASSWORD}'
            NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
            """
        )

        # Create non-superuser, non-bypassrls application role
        await admin_conn.execute(
            f"""
            CREATE ROLE {APP_ROLE}
            LOGIN PASSWORD '{APP_ROLE_PASSWORD}'
            NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
            """
        )

        # Create test database owned by the owner role
        await admin_conn.execute(f"CREATE DATABASE {TEST_DB} OWNER {OWNER_ROLE};")
    finally:
        await admin_conn.close()

    # Connect to the test database as admin to create schema & set ownership
    admin_test_conn = await asyncpg.connect(_admin_dsn(PG_TEST_URL, TEST_DB))
    try:
        # Run schema and RLS setup
        await _apply_schema(admin_test_conn)

        # Transfer ownership of all protected tables to OWNER_ROLE
        protected_tables = [
            "organizations",
            "users",
            "roles",
            "permissions",
            "role_permissions",
            "memberships",
            "membership_roles",
        ]
        for tbl in protected_tables:
            await admin_test_conn.execute(f"ALTER TABLE {tbl} OWNER TO {OWNER_ROLE};")

        # Grant owner and app role schema usage and table privileges
        await admin_test_conn.execute(
            f"""
            GRANT USAGE, CREATE ON SCHEMA public TO {OWNER_ROLE};
            GRANT USAGE ON SCHEMA public TO {APP_ROLE};
            GRANT SELECT, INSERT, UPDATE, DELETE
                ON ALL TABLES IN SCHEMA public TO {APP_ROLE};
            """
        )
    finally:
        await admin_test_conn.close()

    yield {
        "admin_dsn": _admin_dsn(PG_TEST_URL, TEST_DB),
        "app_dsn": _build_dsn(PG_TEST_URL, APP_ROLE, APP_ROLE_PASSWORD, TEST_DB),
        "owner_dsn": _build_dsn(PG_TEST_URL, OWNER_ROLE, OWNER_ROLE_PASSWORD, TEST_DB),
    }

    # Teardown: terminate connections, drop test database and roles
    admin_conn = await asyncpg.connect(PG_TEST_URL)
    try:
        await admin_conn.execute(
            f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{TEST_DB}' AND pid <> pg_backend_pid();
            """
        )
        await admin_conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB};")
        await admin_conn.execute(f"DROP ROLE IF EXISTS {APP_ROLE};")
        await admin_conn.execute(f"DROP ROLE IF EXISTS {OWNER_ROLE};")
    finally:
        await admin_conn.close()


@pytest.fixture
async def app_conn(pg_setup):
    """Connection as the restricted application role."""
    conn = await asyncpg.connect(pg_setup["app_dsn"])
    try:
        yield conn
    finally:
        await conn.close()


@pytest.fixture
async def owner_conn(pg_setup):
    """Connection as the non-superuser table owner (subject to FORCE RLS)."""
    conn = await asyncpg.connect(pg_setup["owner_dsn"])
    try:
        yield conn
    finally:
        await conn.close()


@pytest.fixture
async def admin_conn(pg_setup):
    """Connection as the admin/superuser role (bypasses RLS)."""
    conn = await asyncpg.connect(pg_setup["admin_dsn"])
    try:
        yield conn
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Schema setup (mirrors the Alembic migration)
# ---------------------------------------------------------------------------
async def _apply_schema(conn: asyncpg.Connection) -> None:
    """Apply the schema from 0001_initial_auth_and_tenancy inline.

    Only the tables and policies relevant to roles RLS testing are created.
    """
    await conn.execute(
        """
        -- organizations (minimal for FK target)
        CREATE TABLE IF NOT EXISTS organizations (
            id          UUID PRIMARY KEY,
            name        VARCHAR(255) NOT NULL,
            slug        VARCHAR(100) NOT NULL UNIQUE,
            status      VARCHAR(50) NOT NULL DEFAULT 'active',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        -- users (minimal for FK target)
        CREATE TABLE IF NOT EXISTS users (
            id                UUID PRIMARY KEY,
            email             VARCHAR(255) NOT NULL,
            normalized_email  VARCHAR(255) NOT NULL UNIQUE,
            password_hash     VARCHAR(255) NOT NULL,
            full_name         VARCHAR(255) NOT NULL,
            status            VARCHAR(50) NOT NULL DEFAULT 'active',
            email_verified_at TIMESTAMPTZ,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        -- roles
        CREATE TABLE IF NOT EXISTS roles (
            id              UUID PRIMARY KEY,
            organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
            scope           VARCHAR(20) NOT NULL,
            name            VARCHAR(100) NOT NULL,
            description     VARCHAR(255) NOT NULL DEFAULT '',
            is_system_role  BOOLEAN NOT NULL DEFAULT false,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_roles_scope_org_id CHECK (
                (scope = 'organization' AND organization_id IS NOT NULL)
                OR (scope = 'platform' AND organization_id IS NULL)
            ),
            CONSTRAINT uq_roles_org_id   UNIQUE (organization_id, id),
            CONSTRAINT uq_roles_scope_id UNIQUE (scope, id)
        );

        -- permissions (minimal for FK target)
        CREATE TABLE IF NOT EXISTS permissions (
            id          UUID PRIMARY KEY,
            name        VARCHAR(100) NOT NULL UNIQUE,
            description VARCHAR(255) NOT NULL DEFAULT '',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        -- role_permissions
        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id         UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            permission_id   UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
            role_scope      VARCHAR(20) NOT NULL,
            organization_id UUID,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (role_id, permission_id),
            CONSTRAINT ck_role_permissions_scope_org_id CHECK (
                (role_scope = 'organization' AND organization_id IS NOT NULL)
                OR (role_scope = 'platform' AND organization_id IS NULL)
            ),
            CONSTRAINT fk_role_permissions_composite_org_role
                FOREIGN KEY (organization_id, role_id)
                REFERENCES roles(organization_id, id)
                ON DELETE CASCADE,
            CONSTRAINT fk_role_permissions_composite_scope_role
                FOREIGN KEY (role_scope, role_id)
                REFERENCES roles(scope, id)
                ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS ix_role_permissions_org_id
            ON role_permissions (organization_id);

        -- memberships (minimal)
        CREATE TABLE IF NOT EXISTS memberships (
            id              UUID PRIMARY KEY,
            organization_id UUID NOT NULL REFERENCES organizations(id)
                            ON DELETE CASCADE,
            user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            status          VARCHAR(50) NOT NULL DEFAULT 'active',
            joined_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_memberships_org_user UNIQUE (organization_id, user_id),
            CONSTRAINT uq_memberships_org_id   UNIQUE (organization_id, id)
        );

        -- membership_roles
        CREATE TABLE IF NOT EXISTS membership_roles (
            id              UUID PRIMARY KEY,
            organization_id UUID NOT NULL,
            membership_id   UUID NOT NULL,
            role_id         UUID NOT NULL,
            assigned_by     UUID REFERENCES users(id) ON DELETE SET NULL,
            assigned_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_membership_roles_member_role
                UNIQUE (membership_id, role_id),
            CONSTRAINT fk_membership_roles_composite_org_membership
                FOREIGN KEY (organization_id, membership_id)
                REFERENCES memberships(organization_id, id)
                ON DELETE CASCADE,
            CONSTRAINT fk_membership_roles_composite_org_role
                FOREIGN KEY (organization_id, role_id)
                REFERENCES roles(organization_id, id)
                ON DELETE CASCADE
        );

        -- ================================================================
        -- RLS policies
        -- ================================================================

        -- memberships RLS
        ALTER TABLE memberships ENABLE ROW LEVEL SECURITY;
        ALTER TABLE memberships FORCE ROW LEVEL SECURITY;
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

        -- membership_roles RLS
        ALTER TABLE membership_roles ENABLE ROW LEVEL SECURITY;
        ALTER TABLE membership_roles FORCE ROW LEVEL SECURITY;
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

        -- roles RLS
        ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
        ALTER TABLE roles FORCE ROW LEVEL SECURITY;

        -- SELECT: platform roles always visible; org roles only to tenant
        CREATE POLICY roles_select ON roles
        FOR SELECT
        USING (
            organization_id IS NULL
            OR organization_id = NULLIF(
                current_setting('app.current_org', true), ''
            )::uuid
        );

        -- INSERT: only org-scoped roles for the active tenant
        CREATE POLICY roles_insert ON roles
        FOR INSERT
        WITH CHECK (
            scope = 'organization'
            AND organization_id IS NOT NULL
            AND organization_id = NULLIF(
                current_setting('app.current_org', true), ''
            )::uuid
        );

        -- UPDATE: only org-scoped roles for the active tenant
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

        -- DELETE: only org-scoped roles for the active tenant
        CREATE POLICY roles_delete ON roles
        FOR DELETE
        USING (
            scope = 'organization'
            AND organization_id IS NOT NULL
            AND organization_id = NULLIF(
                current_setting('app.current_org', true), ''
            )::uuid
        );

        -- role_permissions RLS
        ALTER TABLE role_permissions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE role_permissions FORCE ROW LEVEL SECURITY;

        -- SELECT: platform always visible; org roles only to active tenant
        CREATE POLICY role_permissions_select ON role_permissions
        FOR SELECT
        USING (
            organization_id IS NULL
            OR organization_id = NULLIF(
                current_setting('app.current_org', true), ''
            )::uuid
        );

        -- INSERT: only org-scoped role_permissions for the active tenant
        CREATE POLICY role_permissions_insert ON role_permissions
        FOR INSERT
        WITH CHECK (
            role_scope = 'organization'
            AND organization_id IS NOT NULL
            AND organization_id = NULLIF(
                current_setting('app.current_org', true), ''
            )::uuid
        );

        -- UPDATE: only org-scoped role_permissions for the active tenant
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

        -- DELETE: only org-scoped role_permissions for the active tenant
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


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------
async def _seed_data(admin_conn: asyncpg.Connection) -> dict:
    """Insert baseline test data as admin (bypasses RLS).

    Returns a dict with org_a_id, org_b_id, platform_role_id,
    org_a_role_id, org_b_role_id, and permission IDs.
    """
    org_a_id = uuid.uuid4()
    org_b_id = uuid.uuid4()
    platform_role_id = uuid.uuid4()
    org_a_role_id = uuid.uuid4()
    org_b_role_id = uuid.uuid4()
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    membership_a_id = uuid.uuid4()
    membership_b_id = uuid.uuid4()
    perm_platform_id = uuid.uuid4()
    perm_org_a_id = uuid.uuid4()
    perm_org_b_id = uuid.uuid4()

    await admin_conn.execute(
        """
        INSERT INTO organizations (id, name, slug) VALUES
            ($1, 'Org A', 'org-a'),
            ($2, 'Org B', 'org-b');
        """,
        org_a_id,
        org_b_id,
    )
    await admin_conn.execute(
        """
        INSERT INTO roles (id, organization_id, scope, name, description)
        VALUES
            ($1, NULL, 'platform', 'Platform Admin', 'Global admin'),
            ($2, $4,   'organization', 'Org A Admin', 'Admin for A'),
            ($3, $5,   'organization', 'Org B Admin', 'Admin for B');
        """,
        platform_role_id,
        org_a_role_id,
        org_b_role_id,
        org_a_id,
        org_b_id,
    )
    await admin_conn.execute(
        """
        INSERT INTO users (id, email, normalized_email, password_hash, full_name)
        VALUES
            ($1, 'a@example.test', 'a@example.test', 'not-a-real-hash', 'User A'),
            ($2, 'b@example.test', 'b@example.test', 'not-a-real-hash', 'User B');
        """,
        user_a_id,
        user_b_id,
    )
    await admin_conn.execute(
        """
        INSERT INTO memberships (id, organization_id, user_id)
        VALUES ($1, $3, $5), ($2, $4, $6);
        """,
        membership_a_id,
        membership_b_id,
        org_a_id,
        org_b_id,
        user_a_id,
        user_b_id,
    )
    await admin_conn.execute(
        """
        INSERT INTO permissions (id, name, description) VALUES
            ($1, 'system:manage', 'System administration'),
            ($2, 'campaign:create', 'Create campaigns'),
            ($3, 'audit:read', 'Read audit logs');
        """,
        perm_platform_id,
        perm_org_a_id,
        perm_org_b_id,
    )
    await admin_conn.execute(
        """
        INSERT INTO role_permissions
            (role_id, permission_id, role_scope, organization_id)
        VALUES
            ($1, $4, 'platform', NULL),
            ($2, $5, 'organization', $7),
            ($3, $6, 'organization', $8);
        """,
        platform_role_id,
        org_a_role_id,
        org_b_role_id,
        perm_platform_id,
        perm_org_a_id,
        perm_org_b_id,
        org_a_id,
        org_b_id,
    )

    return {
        "org_a_id": org_a_id,
        "org_b_id": org_b_id,
        "platform_role_id": platform_role_id,
        "org_a_role_id": org_a_role_id,
        "org_b_role_id": org_b_role_id,
        "membership_a_id": membership_a_id,
        "membership_b_id": membership_b_id,
        "perm_platform_id": perm_platform_id,
        "perm_org_a_id": perm_org_a_id,
        "perm_org_b_id": perm_org_b_id,
    }


@pytest.fixture
async def seeded(admin_conn, app_conn):
    """Seed data via admin and return IDs. Truncate after each test."""
    data = await _seed_data(admin_conn)
    yield data
    # Clean up (admin bypasses RLS)
    await admin_conn.execute("DELETE FROM role_permissions;")
    await admin_conn.execute("DELETE FROM permissions;")
    await admin_conn.execute("DELETE FROM membership_roles;")
    await admin_conn.execute("DELETE FROM memberships;")
    await admin_conn.execute("DELETE FROM roles;")
    await admin_conn.execute("DELETE FROM organizations;")
    await admin_conn.execute("DELETE FROM users;")


# ---------------------------------------------------------------------------
# Test 1 — Platform roles readable without tenant context
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_platform_roles_readable_without_tenant_context(app_conn, seeded):
    """With no tenant context set, platform roles must be visible."""
    async with app_conn.transaction():
        await app_conn.execute("SELECT set_config('app.current_org', '', true)")
        rows = await app_conn.fetch(
            "SELECT id, scope FROM roles WHERE scope = 'platform'"
        )
    assert len(rows) == 1
    assert rows[0]["id"] == seeded["platform_role_id"]
    assert rows[0]["scope"] == "platform"


# ---------------------------------------------------------------------------
# Test 2 — Organization roles inaccessible without tenant context
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_org_roles_inaccessible_without_tenant_context(app_conn, seeded):
    """Without tenant context, no organization-scoped roles are visible."""
    async with app_conn.transaction():
        await app_conn.execute("SELECT set_config('app.current_org', '', true)")
        rows = await app_conn.fetch("SELECT id FROM roles WHERE scope = 'organization'")
    assert len(rows) == 0, (
        "Organization roles must not be visible without tenant context"
    )


@pytest.mark.asyncio
async def test_membership_rows_require_matching_tenant_context(app_conn, seeded):
    """Membership rows are denied without context and isolated by organization."""
    async with app_conn.transaction():
        rows = await app_conn.fetch("SELECT id FROM memberships")
        assert rows == []

    async with app_conn.transaction():
        await app_conn.execute(
            "SELECT set_config('app.current_org', $1, true)",
            str(seeded["org_a_id"]),
        )
        rows = await app_conn.fetch("SELECT id FROM memberships")
        assert [row["id"] for row in rows] == [seeded["membership_a_id"]]


@pytest.mark.asyncio
async def test_composite_foreign_keys_reject_cross_tenant_relationships(
    admin_conn, seeded
):
    """Even an RLS-bypassing migration/admin path cannot cross tenant FKs."""
    with pytest.raises(asyncpg.ForeignKeyViolationError):
        await admin_conn.execute(
            """
            INSERT INTO membership_roles (id, organization_id, membership_id, role_id)
            VALUES ($1, $2, $3, $4)
            """,
            uuid.uuid4(),
            seeded["org_a_id"],
            seeded["membership_a_id"],
            seeded["org_b_role_id"],
        )

    with pytest.raises(asyncpg.ForeignKeyViolationError):
        await admin_conn.execute(
            """
            INSERT INTO role_permissions
                (role_id, permission_id, role_scope, organization_id)
            VALUES ($1, $2, 'organization', $3)
            """,
            seeded["org_b_role_id"],
            seeded["perm_platform_id"],
            seeded["org_a_id"],
        )


# ---------------------------------------------------------------------------
# Test 3 — Organization A cannot read organization B's roles
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_org_a_cannot_read_org_b_roles(app_conn, seeded):
    """Setting tenant context to org A must hide org B's roles.

    Context setting and query must run in the same transaction block because
    set_config(..., true) is transaction-local.
    """
    async with app_conn.transaction():
        await app_conn.execute(
            "SELECT set_config('app.current_org', $1, true)",
            str(seeded["org_a_id"]),
        )
        rows = await app_conn.fetch(
            "SELECT id, organization_id FROM roles WHERE scope = 'organization'"
        )
        # Should only see org A's role
        assert len(rows) == 1
        assert rows[0]["id"] == seeded["org_a_role_id"]
        assert rows[0]["organization_id"] == seeded["org_a_id"]

        # Explicitly verify org B's role is absent
        row = await app_conn.fetchrow(
            "SELECT id FROM roles WHERE id = $1",
            seeded["org_b_role_id"],
        )
        assert row is None, "Org A context must not see org B's roles"


# ---------------------------------------------------------------------------
# Test 4 — Transaction-local context does not leak on connection reuse
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_transaction_local_context_does_not_leak_on_connection_reuse(
    app_conn, seeded
):
    """A fresh transaction on the same connection starts without tenant context."""
    async with app_conn.transaction():
        await app_conn.execute(
            "SELECT set_config('app.current_org', $1, true)",
            str(seeded["org_a_id"]),
        )
        rows = await app_conn.fetch("SELECT id FROM roles WHERE scope = 'organization'")
        assert [row["id"] for row in rows] == [seeded["org_a_role_id"]]

    # The same physical app connection is reused without a context.
    async with app_conn.transaction():
        rows = await app_conn.fetch("SELECT id FROM roles WHERE scope = 'organization'")
        assert rows == []

    async with app_conn.transaction():
        await app_conn.execute(
            "SELECT set_config('app.current_org', $1, true)",
            str(seeded["org_b_id"]),
        )
        rows = await app_conn.fetch("SELECT id FROM roles WHERE scope = 'organization'")
        assert [row["id"] for row in rows] == [seeded["org_b_role_id"]]


# ---------------------------------------------------------------------------
# Test 5 — Organization A cannot INSERT/UPDATE/DELETE organization B's roles
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_org_a_cannot_mutate_org_b_roles(app_conn, admin_conn, seeded):
    """INSERT, UPDATE, and DELETE against org B's roles must fail
    when tenant context is set to org A.

    Each operation executes in its own transaction block so a failed
    statement does not abort subsequent operations.
    """
    new_id = uuid.uuid4()
    # INSERT into org B should fail (RLS WITH CHECK violation)
    with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
        async with app_conn.transaction():
            await app_conn.execute(
                "SELECT set_config('app.current_org', $1, true)",
                str(seeded["org_a_id"]),
            )
            await app_conn.execute(
                """
                INSERT INTO roles (id, organization_id, scope, name, description)
                VALUES ($1, $2, 'organization', 'Sneaky Role', 'cross-tenant');
                """,
                new_id,
                seeded["org_b_id"],
            )

    # UPDATE org B's role: should silently affect 0 rows
    # (USING clause hides the row, so no match)
    async with app_conn.transaction():
        await app_conn.execute(
            "SELECT set_config('app.current_org', $1, true)",
            str(seeded["org_a_id"]),
        )
        result = await app_conn.execute(
            "UPDATE roles SET name = 'Hacked' WHERE id = $1",
            seeded["org_b_role_id"],
        )
        assert result == "UPDATE 0", (
            "UPDATE against another org's role must affect 0 rows"
        )

    # DELETE org B's role: should silently affect 0 rows
    async with app_conn.transaction():
        await app_conn.execute(
            "SELECT set_config('app.current_org', $1, true)",
            str(seeded["org_a_id"]),
        )
        result = await app_conn.execute(
            "DELETE FROM roles WHERE id = $1",
            seeded["org_b_role_id"],
        )
        assert result == "DELETE 0", (
            "DELETE against another org's role must affect 0 rows"
        )

    # Confirm org B's role still exists (via admin)
    row = await admin_conn.fetchrow(
        "SELECT id FROM roles WHERE id = $1",
        seeded["org_b_role_id"],
    )
    assert row is not None, "Org B's role must still exist after failed mutations"


# ---------------------------------------------------------------------------
# Test 5 — Ordinary application role cannot create platform roles
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_app_role_cannot_create_platform_roles(app_conn, seeded):
    """The INSERT policy requires scope='organization', so inserting a
    platform role must fail regardless of tenant context.
    """
    # With tenant context set (so the role can do *something*)
    new_id = uuid.uuid4()
    with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
        async with app_conn.transaction():
            await app_conn.execute(
                "SELECT set_config('app.current_org', $1, true)",
                str(seeded["org_a_id"]),
            )
            await app_conn.execute(
                """
                INSERT INTO roles (id, organization_id, scope, name, description)
                VALUES ($1, NULL, 'platform', 'Evil Platform Role', 'nope');
                """,
                new_id,
            )

    # Without tenant context
    with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
        async with app_conn.transaction():
            await app_conn.execute("SELECT set_config('app.current_org', '', true)")
            await app_conn.execute(
                """
                INSERT INTO roles (id, organization_id, scope, name, description)
                VALUES ($1, NULL, 'platform', 'Evil Platform Role 2', 'nope');
                """,
                uuid.uuid4(),
            )


# ---------------------------------------------------------------------------
# Test 6 — Verify FORCE ROW LEVEL SECURITY is active for table owner
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_force_rls_is_active_for_owner(owner_conn, seeded):
    """A non-superuser table owner has RLS enforced when FORCE ROW LEVEL SECURITY
    is enabled. Without explicit tenant context, org roles must be invisible
    to the owner too.
    """
    async with owner_conn.transaction():
        await owner_conn.execute("SELECT set_config('app.current_org', '', true)")
        rows = await owner_conn.fetch("SELECT id, scope FROM roles")
    # Only platform roles should be visible
    scopes = {r["scope"] for r in rows}
    ids = {r["id"] for r in rows}
    assert "organization" not in scopes, (
        "FORCE RLS must hide org roles from the table owner too"
    )
    assert seeded["platform_role_id"] in ids

    # With tenant context set, the owner only sees that organization's roles
    async with owner_conn.transaction():
        await owner_conn.execute(
            "SELECT set_config('app.current_org', $1, true)",
            str(seeded["org_a_id"]),
        )
        org_a_rows = await owner_conn.fetch(
            "SELECT id, scope FROM roles WHERE scope = 'organization'"
        )
    assert len(org_a_rows) == 1
    assert org_a_rows[0]["id"] == seeded["org_a_role_id"]


# ---------------------------------------------------------------------------
# Test 7 — Roles privileges: no SUPERUSER, no BYPASSRLS
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_app_role_has_no_elevated_privileges(admin_conn):
    """Confirm application and owner roles have neither SUPERUSER nor BYPASSRLS."""
    for role_name in (APP_ROLE, OWNER_ROLE):
        row = await admin_conn.fetchrow(
            """
            SELECT rolsuper, rolbypassrls
            FROM pg_catalog.pg_roles
            WHERE rolname = $1;
            """,
            role_name,
        )
        assert row is not None, f"Role {role_name} must exist"
        assert row["rolsuper"] is False, f"Role {role_name} must not be SUPERUSER"
        assert row["rolbypassrls"] is False, f"Role {role_name} must not have BYPASSRLS"


# ---------------------------------------------------------------------------
# Test 8 — App role does not own protected tables
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_app_role_does_not_own_protected_tables(admin_conn):
    """The application role must not own the tenant-protected tables."""
    protected = ("roles", "role_permissions", "memberships", "membership_roles")
    for table in protected:
        row = await admin_conn.fetchrow(
            """
            SELECT tableowner
            FROM pg_catalog.pg_tables
            WHERE tablename = $1 AND schemaname = 'public';
            """,
            table,
        )
        assert row is not None, f"Table {table} must exist"
        assert row["tableowner"] != APP_ROLE, f"App role must not own table {table}"
        assert row["tableowner"] == OWNER_ROLE, f"Owner role must own table {table}"


# ---------------------------------------------------------------------------
# Test 9 — Migration upgrade/downgrade cycle (Alembic)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_migration_upgrade_downgrade(pg_setup):
    """Verify the Alembic migration can be applied and reverted on a
    fresh disposable database.

    This test creates a second temporary database, runs Alembic upgrade
    and downgrade using subprocess, and verifies both succeed.
    """
    import subprocess
    import sys

    cycle_db = "sandeshvani_rls_cycle_test"
    admin_conn = await asyncpg.connect(PG_TEST_URL)

    try:
        # Clean up any prior run
        await admin_conn.execute(
            f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{cycle_db}' AND pid <> pg_backend_pid();
            """
        )
        await admin_conn.execute(f"DROP DATABASE IF EXISTS {cycle_db};")

        # Ensure sandeshvani_owner role exists and current user can assume it
        admin_user = urlsplit(PG_TEST_URL).username or "postgres"
        await admin_conn.execute(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT FROM pg_roles WHERE rolname = 'sandeshvani_owner'
                ) THEN
                    CREATE ROLE sandeshvani_owner NOLOGIN;
                END IF;
            END
            $$;
            GRANT sandeshvani_owner TO "{admin_user}";
            """
        )
        await admin_conn.execute(f"CREATE DATABASE {cycle_db} OWNER sandeshvani_owner;")
    finally:
        await admin_conn.close()

    cycle_dsn = _admin_dsn(PG_TEST_URL, cycle_db)

    # Ensure sandeshvani_owner has schema privileges in cycle_db
    cycle_setup_conn = await asyncpg.connect(cycle_dsn)
    try:
        await cycle_setup_conn.execute(
            "GRANT ALL ON SCHEMA public TO sandeshvani_owner;"
        )
    finally:
        await cycle_setup_conn.close()

    # Convert asyncpg DSN to SQLAlchemy format
    sa_url = cycle_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)

    env = {
        **os.environ,
        "DATABASE_URL": sa_url,
        "MIGRATION_DATABASE_URL": sa_url,
        "MIGRATION_DATABASE_ROLE": "sandeshvani_owner",
        "PYTHONPATH": "backend",
    }

    try:
        # Upgrade
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "-c",
                "backend/alembic.ini",
                "upgrade",
                "head",
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
            cwd=os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
        )
        assert result.returncode == 0, (
            f"Alembic upgrade failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

        # Verify RLS is enabled and forced on all protected tenant tables.
        verify_conn = await asyncpg.connect(cycle_dsn)
        try:
            protected_tables = (
                "roles",
                "role_permissions",
                "audience_members",
                "audience_import_uploads",
                "audience_import_jobs",
                "audience_import_job_errors",
                "outbox_events",
            )
            for table in protected_tables:
                row = await verify_conn.fetchrow(
                    """
                    SELECT c.relrowsecurity, c.relforcerowsecurity
                    FROM pg_class AS c
                    JOIN pg_namespace AS n ON n.oid = c.relnamespace
                    WHERE n.nspname = 'public' AND c.relname = $1;
                    """,
                    table,
                )
                assert row is not None, f"Table {table} not found in pg_class"
                assert row["relrowsecurity"] is True, f"RLS not enabled on {table}"
                assert row["relforcerowsecurity"] is True, (
                    f"FORCE RLS not enabled on {table}"
                )

            for table in (
                "audience_members",
                "audience_import_uploads",
                "audience_import_jobs",
                "audience_import_job_errors",
                "outbox_events",
            ):
                policy = await verify_conn.fetchrow(
                    """
                    SELECT policyname, cmd, qual, with_check
                    FROM pg_policies
                    WHERE schemaname = 'public'
                      AND tablename = $1
                      AND policyname = 'tenant_isolation';
                    """,
                    table,
                )
                assert policy is not None, f"tenant_isolation policy missing on {table}"
                assert policy["cmd"] == "ALL", (
                    f"tenant_isolation must cover all commands on {table}"
                )
                assert policy["qual"] and "app.current_org" in policy["qual"], (
                    f"tenant_isolation USING clause must scope {table}"
                )
                assert (
                    policy["with_check"] is not None
                    and "app.current_org" in policy["with_check"]
                ), f"tenant_isolation WITH CHECK clause must scope {table}"

            # The audience tables must be owned by the migration role, not
            # by the ordinary runtime application role.
            for table in (
                "audience_members",
                "audience_import_uploads",
                "audience_import_jobs",
                "audience_import_job_errors",
                "outbox_events",
            ):
                ownership = await verify_conn.fetchrow(
                    """
                    SELECT tableowner
                    FROM pg_catalog.pg_tables
                    WHERE schemaname = 'public' AND tablename = $1;
                    """,
                    table,
                )
                assert ownership is not None, f"Table {table} must exist"
                assert ownership["tableowner"] == "sandeshvani_owner", (
                    f"Migration role must own table {table}"
                )
        finally:
            await verify_conn.close()

        # AUD-04 identity keys are enforced by tenant-scoped unique indexes.
        for index_name in (
            "uq_audience_members_org_email_identity",
            "uq_audience_members_org_phone_identity",
        ):
            index = await verify_conn.fetchrow(
                """
                SELECT indexdef
                FROM pg_indexes
                WHERE schemaname = 'public' AND indexname = $1;
                """,
                index_name,
            )
            assert index is not None, f"Identity index {index_name} is missing"
            assert "CREATE UNIQUE INDEX" in index["indexdef"]
            assert "organization_id" in index["indexdef"]
            assert "WHERE" in index["indexdef"]

        # Downgrade
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "-c",
                "backend/alembic.ini",
                "downgrade",
                "base",
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
            cwd=os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
        )
        assert result.returncode == 0, (
            f"Alembic downgrade failed:\nstdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )
    finally:
        # Teardown cycle database
        admin_conn = await asyncpg.connect(PG_TEST_URL)
        try:
            await admin_conn.execute(
                f"""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = '{cycle_db}' AND pid <> pg_backend_pid();
                """
            )
            await admin_conn.execute(f"DROP DATABASE IF EXISTS {cycle_db};")
        finally:
            await admin_conn.close()


# ---------------------------------------------------------------------------
# Test 10 — Platform role permissions readable without tenant context
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_platform_role_permissions_readable_without_tenant_context(
    app_conn, seeded
):
    """With no tenant context set, platform role permissions must be visible."""
    async with app_conn.transaction():
        await app_conn.execute("SELECT set_config('app.current_org', '', true)")
        rows = await app_conn.fetch(
            "SELECT role_id, permission_id, role_scope, organization_id "
            "FROM role_permissions WHERE role_scope = 'platform'"
        )
    assert len(rows) == 1
    assert rows[0]["role_id"] == seeded["platform_role_id"]
    assert rows[0]["permission_id"] == seeded["perm_platform_id"]
    assert rows[0]["role_scope"] == "platform"
    assert rows[0]["organization_id"] is None


# ---------------------------------------------------------------------------
# Test 11 — Organization role permissions inaccessible without tenant context
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_org_role_permissions_inaccessible_without_tenant_context(
    app_conn, seeded
):
    """Without tenant context, no organization-scoped role permissions are visible."""
    async with app_conn.transaction():
        await app_conn.execute("SELECT set_config('app.current_org', '', true)")
        rows = await app_conn.fetch(
            "SELECT role_id, permission_id FROM role_permissions "
            "WHERE role_scope = 'organization'"
        )
    assert len(rows) == 0, (
        "Organization role permissions must not be visible without tenant context"
    )


# ---------------------------------------------------------------------------
# Test 12 — Organization A can read own role permissions
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_org_a_can_read_own_role_permissions(app_conn, seeded):
    """With tenant context set to Org A, Org A sees its own role permissions."""
    async with app_conn.transaction():
        await app_conn.execute(
            "SELECT set_config('app.current_org', $1, true)",
            str(seeded["org_a_id"]),
        )
        rows = await app_conn.fetch(
            "SELECT role_id, permission_id, organization_id FROM role_permissions "
            "WHERE role_scope = 'organization'"
        )
    assert len(rows) == 1
    assert rows[0]["role_id"] == seeded["org_a_role_id"]
    assert rows[0]["permission_id"] == seeded["perm_org_a_id"]
    assert rows[0]["organization_id"] == seeded["org_a_id"]


# ---------------------------------------------------------------------------
# Test 13 — Organization A cannot read organization B's role permissions
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_org_a_cannot_read_org_b_role_permissions(app_conn, seeded):
    """Setting tenant context to Org A must hide Org B's role permissions."""
    async with app_conn.transaction():
        await app_conn.execute(
            "SELECT set_config('app.current_org', $1, true)",
            str(seeded["org_a_id"]),
        )
        # Querying by Org B's organization_id returns 0 rows
        rows = await app_conn.fetch(
            "SELECT role_id, permission_id FROM role_permissions "
            "WHERE organization_id = $1",
            seeded["org_b_id"],
        )
        assert len(rows) == 0

        # Directly querying Org B's association returns None
        row = await app_conn.fetchrow(
            "SELECT * FROM role_permissions WHERE role_id = $1 AND permission_id = $2",
            seeded["org_b_role_id"],
            seeded["perm_org_b_id"],
        )
        assert row is None, "Org A context must not see Org B's role permissions"


# ---------------------------------------------------------------------------
# Test 14 — Organization A cannot insert role permissions for organization B
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_org_a_cannot_insert_role_permission_for_org_b(app_conn, seeded):
    """Inserting a role permission for Org B while in Org A context must fail
    with InsufficientPrivilegeError (RLS WITH CHECK violation).
    """
    with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
        async with app_conn.transaction():
            await app_conn.execute(
                "SELECT set_config('app.current_org', $1, true)",
                str(seeded["org_a_id"]),
            )
            await app_conn.execute(
                """
                INSERT INTO role_permissions
                    (role_id, permission_id, role_scope, organization_id)
                VALUES ($1, $2, 'organization', $3);
                """,
                seeded["org_b_role_id"],
                seeded["perm_platform_id"],
                seeded["org_b_id"],
            )

    # Without tenant context, inserting an org role permission also fails
    with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
        async with app_conn.transaction():
            await app_conn.execute("SELECT set_config('app.current_org', '', true)")
            await app_conn.execute(
                """
                INSERT INTO role_permissions
                    (role_id, permission_id, role_scope, organization_id)
                VALUES ($1, $2, 'organization', $3);
                """,
                seeded["org_a_role_id"],
                seeded["perm_platform_id"],
                seeded["org_a_id"],
            )


# ---------------------------------------------------------------------------
# Test 15 — Organization A cannot UPDATE/DELETE organization B's role permissions
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_org_a_cannot_mutate_org_b_role_permissions(app_conn, admin_conn, seeded):
    """UPDATE and DELETE against Org B's role permissions must affect 0 rows
    when tenant context is set to Org A.
    """
    # UPDATE org B's role permission: should affect 0 rows
    async with app_conn.transaction():
        await app_conn.execute(
            "SELECT set_config('app.current_org', $1, true)",
            str(seeded["org_a_id"]),
        )
        result = await app_conn.execute(
            """
            UPDATE role_permissions
            SET role_scope = 'organization'
            WHERE role_id = $1 AND permission_id = $2;
            """,
            seeded["org_b_role_id"],
            seeded["perm_org_b_id"],
        )
        assert result == "UPDATE 0", (
            "UPDATE against another org's role permissions must affect 0 rows"
        )

    # DELETE org B's role permission: should affect 0 rows
    async with app_conn.transaction():
        await app_conn.execute(
            "SELECT set_config('app.current_org', $1, true)",
            str(seeded["org_a_id"]),
        )
        result = await app_conn.execute(
            "DELETE FROM role_permissions WHERE role_id = $1 AND permission_id = $2;",
            seeded["org_b_role_id"],
            seeded["perm_org_b_id"],
        )
        assert result == "DELETE 0", (
            "DELETE against another org's role permissions must affect 0 rows"
        )

    # Confirm Org B's role permission still exists (via admin)
    row = await admin_conn.fetchrow(
        "SELECT * FROM role_permissions WHERE role_id = $1 AND permission_id = $2;",
        seeded["org_b_role_id"],
        seeded["perm_org_b_id"],
    )
    assert row is not None, (
        "Org B's role permission must still exist after failed mutation attempts"
    )


# ---------------------------------------------------------------------------
# Test 16 — Ordinary application role cannot create or mutate platform role permissions
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_app_role_cannot_create_or_mutate_platform_role_permissions(
    app_conn, seeded
):
    """The app role cannot insert, update, or delete platform role permissions."""
    # INSERT with tenant context set fails RLS WITH CHECK
    with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
        async with app_conn.transaction():
            await app_conn.execute(
                "SELECT set_config('app.current_org', $1, true)",
                str(seeded["org_a_id"]),
            )
            await app_conn.execute(
                """
                INSERT INTO role_permissions
                    (role_id, permission_id, role_scope, organization_id)
                VALUES ($1, $2, 'platform', NULL);
                """,
                seeded["platform_role_id"],
                seeded["perm_org_a_id"],
            )

    # INSERT without tenant context fails RLS WITH CHECK
    with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
        async with app_conn.transaction():
            await app_conn.execute("SELECT set_config('app.current_org', '', true)")
            await app_conn.execute(
                """
                INSERT INTO role_permissions
                    (role_id, permission_id, role_scope, organization_id)
                VALUES ($1, $2, 'platform', NULL);
                """,
                seeded["platform_role_id"],
                seeded["perm_org_a_id"],
            )

    # UPDATE platform role permission affects 0 rows
    async with app_conn.transaction():
        await app_conn.execute(
            "SELECT set_config('app.current_org', $1, true)",
            str(seeded["org_a_id"]),
        )
        result = await app_conn.execute(
            """
            UPDATE role_permissions
            SET role_scope = 'platform'
            WHERE role_id = $1 AND permission_id = $2;
            """,
            seeded["platform_role_id"],
            seeded["perm_platform_id"],
        )
        assert result == "UPDATE 0"

    # DELETE platform role permission affects 0 rows
    async with app_conn.transaction():
        await app_conn.execute(
            "SELECT set_config('app.current_org', $1, true)",
            str(seeded["org_a_id"]),
        )
        result = await app_conn.execute(
            "DELETE FROM role_permissions WHERE role_id = $1 AND permission_id = $2;",
            seeded["platform_role_id"],
            seeded["perm_platform_id"],
        )
        assert result == "DELETE 0"


# ---------------------------------------------------------------------------
# Test 17 — FORCE ROW LEVEL SECURITY applies to owner on role_permissions
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_force_rls_is_active_for_owner_on_role_permissions(owner_conn, seeded):
    """A non-superuser table owner has RLS enforced on role_permissions when
    FORCE ROW LEVEL SECURITY is enabled.
    """
    # Without tenant context, owner only sees platform role permissions
    async with owner_conn.transaction():
        await owner_conn.execute("SELECT set_config('app.current_org', '', true)")
        rows = await owner_conn.fetch(
            "SELECT role_id, permission_id, role_scope FROM role_permissions"
        )
    scopes = {r["role_scope"] for r in rows}
    assert "organization" not in scopes, (
        "FORCE RLS must hide org role permissions from table owner "
        "without tenant context"
    )
    assert len(rows) == 1
    assert rows[0]["role_id"] == seeded["platform_role_id"]

    # With Org A context, owner sees Org A and platform, but not Org B
    async with owner_conn.transaction():
        await owner_conn.execute(
            "SELECT set_config('app.current_org', $1, true)",
            str(seeded["org_a_id"]),
        )
        org_a_rows = await owner_conn.fetch(
            "SELECT role_id, permission_id FROM role_permissions "
            "WHERE role_scope = 'organization'"
        )
    assert len(org_a_rows) == 1
    assert org_a_rows[0]["role_id"] == seeded["org_a_role_id"]
    assert org_a_rows[0]["permission_id"] == seeded["perm_org_a_id"]
