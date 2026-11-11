"""PostgreSQL integration tests for P0.4 — refresh-token rotation, replay
detection, family revocation, and session lifecycle.

These tests run against a real PostgreSQL instance and validate:
  1. Single-use token rotation with ``rotated_at`` tracking.
  2. Replay detection (presenting an already-rotated token revokes the family).
  3. Family-wide revocation propagation.
  4. Logout revokes session and individual token.
  5. Logout-all revokes every session for a user.
  6. Atomic compare-and-swap prevents double-consumption.
  7. Migration 0003 columns (rotated_at, revoked_at, replaced_by_id) exist.

Prerequisites
-------------
Set ``SANDESHVANI_PG_TEST_URL`` to a PostgreSQL connection string (user must
have CREATEDB privilege or be a superuser)::

    export SANDESHVANI_PG_TEST_URL="postgresql://bakhtiarsiddiqui@localhost:5432/postgres"

Run with::

    SANDESHVANI_PG_TEST_URL="postgresql://..." \\
        PYTHONPATH=backend pytest -c backend/pyproject.toml \\
        backend/tests/test_refresh_token_pg.py -v
"""

from __future__ import annotations

import hashlib
import os
import secrets
import subprocess
import sys
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit, urlunsplit

import pytest

asyncpg = pytest.importorskip("asyncpg", reason="asyncpg required for PG integration")

PG_TEST_URL = os.environ.get("SANDESHVANI_PG_TEST_URL", "")
if not PG_TEST_URL:
    pytest.skip(
        "SANDESHVANI_PG_TEST_URL not set — skipping PostgreSQL refresh-token tests",
        allow_module_level=True,
    )

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
REFRESH_DB = "sandeshvani_refresh_test"


def _admin_dsn(base_url: str, dbname: str) -> str:
    parsed = urlsplit(base_url)
    return urlunsplit(
        (parsed.scheme, parsed.netloc, f"/{dbname}", parsed.query, parsed.fragment)
    )


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _gen_token() -> str:
    return secrets.token_urlsafe(48)


# ---------------------------------------------------------------------------
# Fixture — disposable database with auth tables
# ---------------------------------------------------------------------------


@pytest.fixture
async def pg_refresh_db():
    """Create a disposable database with auth_sessions + refresh_tokens tables.

    Yields a DSN string for the test database.
    """
    admin_conn = await asyncpg.connect(PG_TEST_URL)
    try:
        await admin_conn.execute(
            f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{REFRESH_DB}' AND pid <> pg_backend_pid();
            """
        )
        await admin_conn.execute(f"DROP DATABASE IF EXISTS {REFRESH_DB};")
        await admin_conn.execute(f"CREATE DATABASE {REFRESH_DB};")
    finally:
        await admin_conn.close()

    dsn = _admin_dsn(PG_TEST_URL, REFRESH_DB)
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute("""
            CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

            CREATE TABLE users (
                id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                email       VARCHAR(255) NOT NULL UNIQUE,
                status      VARCHAR(20) NOT NULL DEFAULT 'active'
            );

            CREATE TABLE auth_sessions (
                id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                ip_address  VARCHAR(100),
                user_agent  VARCHAR(500),
                created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
                expires_at  TIMESTAMPTZ NOT NULL,
                revoked_at  TIMESTAMPTZ
            );
            CREATE INDEX ON auth_sessions(user_id);

            CREATE TABLE refresh_tokens (
                id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                session_id      UUID NOT NULL
                    REFERENCES auth_sessions(id) ON DELETE CASCADE,
                token_hash      VARCHAR(64) NOT NULL UNIQUE,
                family_id       UUID NOT NULL,
                is_revoked      BOOLEAN NOT NULL DEFAULT false,
                rotated_at      TIMESTAMPTZ,
                revoked_at      TIMESTAMPTZ,
                replaced_by_id  UUID REFERENCES refresh_tokens(id) ON DELETE SET NULL,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
                expires_at      TIMESTAMPTZ NOT NULL
            );
            CREATE INDEX ON refresh_tokens(session_id);
            CREATE INDEX ON refresh_tokens(family_id);
            CREATE UNIQUE INDEX ON refresh_tokens(token_hash);
        """)
    finally:
        await conn.close()

    yield dsn

    # Teardown
    admin_conn = await asyncpg.connect(PG_TEST_URL)
    try:
        await admin_conn.execute(
            f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{REFRESH_DB}' AND pid <> pg_backend_pid();
            """
        )
        await admin_conn.execute(f"DROP DATABASE IF EXISTS {REFRESH_DB};")
    finally:
        await admin_conn.close()


@pytest.fixture
async def conn(pg_refresh_db):
    """Single connection to the test database."""
    c = await asyncpg.connect(pg_refresh_db)
    try:
        yield c
    finally:
        await c.close()


# ---------------------------------------------------------------------------
# Helpers — insert test data
# ---------------------------------------------------------------------------


async def _create_user(conn, email: str = "test@example.com") -> uuid.UUID:
    return await conn.fetchval(
        "INSERT INTO users (email) VALUES ($1) RETURNING id", email
    )


async def _create_session(
    conn,
    user_id: uuid.UUID,
    expires_days: int = 7,
) -> uuid.UUID:
    now = datetime.now(UTC)
    return await conn.fetchval(
        """
        INSERT INTO auth_sessions (user_id, created_at, expires_at)
        VALUES ($1, $2, $3)
        RETURNING id
        """,
        user_id,
        now,
        now + timedelta(days=expires_days),
    )


async def _create_refresh_token(
    conn,
    session_id: uuid.UUID,
    family_id: uuid.UUID,
    raw_token: str | None = None,
    expires_days: int = 7,
) -> tuple[uuid.UUID, str, str]:
    """Insert a refresh token. Returns (token_id, raw_token, token_hash)."""
    if raw_token is None:
        raw_token = _gen_token()
    t_hash = _hash_token(raw_token)
    now = datetime.now(UTC)
    token_id = await conn.fetchval(
        """
        INSERT INTO refresh_tokens
            (session_id, token_hash, family_id, created_at, expires_at)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
        """,
        session_id,
        t_hash,
        family_id,
        now,
        now + timedelta(days=expires_days),
    )
    return token_id, raw_token, t_hash


async def _consume_token(conn, token_id: uuid.UUID) -> bool:
    """Atomic compare-and-swap: mark token as rotated if still active."""
    now = datetime.now(UTC)
    result = await conn.fetchval(
        """
        UPDATE refresh_tokens
        SET rotated_at = $1
        WHERE id = $2
          AND rotated_at IS NULL
          AND revoked_at IS NULL
          AND expires_at > $1
        RETURNING id
        """,
        now,
        token_id,
    )
    return result is not None


async def _revoke_family(conn, family_id: uuid.UUID) -> int:
    """Revoke all tokens in a family."""
    now = datetime.now(UTC)
    return await conn.fetchval(
        """
        WITH revoked AS (
            UPDATE refresh_tokens
            SET is_revoked = true, revoked_at = $1
            WHERE family_id = $2
            RETURNING id
        )
        SELECT count(*) FROM revoked
        """,
        now,
        family_id,
    )


async def _revoke_session(conn, session_id: uuid.UUID) -> None:
    await conn.execute(
        "UPDATE auth_sessions SET revoked_at = $1 WHERE id = $2",
        datetime.now(UTC),
        session_id,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_migration_0003_columns_exist(conn):
    """Verify the lifecycle columns added by migration 0003 are present."""
    columns = await conn.fetch(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'refresh_tokens'
          AND column_name IN ('rotated_at', 'revoked_at', 'replaced_by_id')
        ORDER BY column_name
        """
    )
    col_map = {row["column_name"]: row["data_type"] for row in columns}
    assert "replaced_by_id" in col_map
    assert "revoked_at" in col_map
    assert "rotated_at" in col_map
    assert col_map["replaced_by_id"] == "uuid"
    assert "timestamp" in col_map["revoked_at"]
    assert "timestamp" in col_map["rotated_at"]


@pytest.mark.asyncio
async def test_single_use_rotation(conn):
    """A token can be consumed exactly once; second attempt fails."""
    user_id = await _create_user(conn)
    session_id = await _create_session(conn, user_id)
    family_id = uuid.uuid4()
    token_id, _, _ = await _create_refresh_token(conn, session_id, family_id)

    # First consume succeeds
    assert await _consume_token(conn, token_id) is True

    # Second consume of the same token fails (rotated_at is now set)
    assert await _consume_token(conn, token_id) is False


@pytest.mark.asyncio
async def test_rotation_sets_rotated_at(conn):
    """After consumption, rotated_at is set and is a recent timestamp."""
    user_id = await _create_user(conn)
    session_id = await _create_session(conn, user_id)
    family_id = uuid.uuid4()
    token_id, _, _ = await _create_refresh_token(conn, session_id, family_id)

    before = datetime.now(UTC)
    await _consume_token(conn, token_id)
    after = datetime.now(UTC)

    row = await conn.fetchrow(
        "SELECT rotated_at FROM refresh_tokens WHERE id = $1", token_id
    )
    assert row["rotated_at"] is not None
    assert before <= row["rotated_at"].replace(tzinfo=UTC) <= after


@pytest.mark.asyncio
async def test_replaced_by_id_linking(conn):
    """After rotation, the old token is linked to its replacement via replaced_by_id."""
    user_id = await _create_user(conn)
    session_id = await _create_session(conn, user_id)
    family_id = uuid.uuid4()

    old_id, _, _ = await _create_refresh_token(conn, session_id, family_id)
    await _consume_token(conn, old_id)

    # Issue replacement in same family
    new_id, _, _ = await _create_refresh_token(conn, session_id, family_id)

    # Link old → new
    await conn.execute(
        "UPDATE refresh_tokens SET replaced_by_id = $1 WHERE id = $2",
        new_id,
        old_id,
    )

    row = await conn.fetchrow(
        "SELECT replaced_by_id FROM refresh_tokens WHERE id = $1", old_id
    )
    assert row["replaced_by_id"] == new_id


@pytest.mark.asyncio
async def test_replay_triggers_family_revocation(conn):
    """Presenting an already-rotated token revokes the entire family."""
    user_id = await _create_user(conn)
    session_id = await _create_session(conn, user_id)
    family_id = uuid.uuid4()

    # Create first token and rotate it
    old_id, _, _ = await _create_refresh_token(conn, session_id, family_id)
    assert await _consume_token(conn, old_id) is True

    # Issue replacement
    new_id, _, _ = await _create_refresh_token(conn, session_id, family_id)

    # Simulate replay: attempt to consume old token again — it fails
    assert await _consume_token(conn, old_id) is False

    # Detect replay: old token has rotated_at set → revoke entire family
    old_row = await conn.fetchrow(
        "SELECT rotated_at FROM refresh_tokens WHERE id = $1", old_id
    )
    assert old_row["rotated_at"] is not None

    revoked_count = await _revoke_family(conn, family_id)
    assert revoked_count == 2  # Both old and new tokens in the family

    # Verify both tokens are revoked
    rows = await conn.fetch(
        "SELECT id, is_revoked, revoked_at FROM refresh_tokens WHERE family_id = $1",
        family_id,
    )
    for row in rows:
        assert row["is_revoked"] is True
        assert row["revoked_at"] is not None


@pytest.mark.asyncio
async def test_replay_revokes_session(conn):
    """Replay detection also revokes the associated auth session."""
    user_id = await _create_user(conn)
    session_id = await _create_session(conn, user_id)
    family_id = uuid.uuid4()

    token_id, _, _ = await _create_refresh_token(conn, session_id, family_id)
    await _consume_token(conn, token_id)

    # Simulate replay detection → revoke session
    await _revoke_session(conn, session_id)

    row = await conn.fetchrow(
        "SELECT revoked_at FROM auth_sessions WHERE id = $1", session_id
    )
    assert row["revoked_at"] is not None


@pytest.mark.asyncio
async def test_revoked_token_cannot_be_consumed(conn):
    """A token that has been explicitly revoked cannot be consumed."""
    user_id = await _create_user(conn)
    session_id = await _create_session(conn, user_id)
    family_id = uuid.uuid4()

    token_id, _, _ = await _create_refresh_token(conn, session_id, family_id)

    # Revoke the token before any rotation attempt
    await conn.execute(
        "UPDATE refresh_tokens SET is_revoked = true, revoked_at = $1 WHERE id = $2",
        datetime.now(UTC),
        token_id,
    )

    # Consume should fail because revoked_at IS NOT NULL
    assert await _consume_token(conn, token_id) is False


@pytest.mark.asyncio
async def test_expired_token_cannot_be_consumed(conn):
    """A token past its expiry cannot be consumed even if not revoked."""
    user_id = await _create_user(conn)
    session_id = await _create_session(conn, user_id)
    family_id = uuid.uuid4()

    # Create token with -1 day expiry (already expired)
    token_id, _, _ = await _create_refresh_token(
        conn, session_id, family_id, expires_days=-1
    )

    assert await _consume_token(conn, token_id) is False


@pytest.mark.asyncio
async def test_logout_revokes_session_and_token(conn):
    """Logout revokes both the auth session and the current refresh token."""
    user_id = await _create_user(conn)
    session_id = await _create_session(conn, user_id)
    family_id = uuid.uuid4()

    token_id, _, _ = await _create_refresh_token(conn, session_id, family_id)

    # Logout: revoke session + individual token
    await _revoke_session(conn, session_id)
    now = datetime.now(UTC)
    await conn.execute(
        "UPDATE refresh_tokens SET is_revoked = true, revoked_at = $1 WHERE id = $2",
        now,
        token_id,
    )

    # Session is revoked
    session_row = await conn.fetchrow(
        "SELECT revoked_at FROM auth_sessions WHERE id = $1", session_id
    )
    assert session_row["revoked_at"] is not None

    # Token is revoked
    token_row = await conn.fetchrow(
        "SELECT is_revoked, revoked_at FROM refresh_tokens WHERE id = $1", token_id
    )
    assert token_row["is_revoked"] is True
    assert token_row["revoked_at"] is not None

    # Consume should fail
    assert await _consume_token(conn, token_id) is False


@pytest.mark.asyncio
async def test_logout_all_revokes_all_user_sessions(conn):
    """Logout-all revokes every session belonging to the user."""
    user_id = await _create_user(conn)
    s1 = await _create_session(conn, user_id)
    s2 = await _create_session(conn, user_id)
    s3 = await _create_session(conn, user_id)

    family1, family2, family3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    t1, _, _ = await _create_refresh_token(conn, s1, family1)
    t2, _, _ = await _create_refresh_token(conn, s2, family2)
    t3, _, _ = await _create_refresh_token(conn, s3, family3)

    # Logout-all: revoke all un-revoked sessions for user
    now = datetime.now(UTC)
    await conn.execute(
        """
        UPDATE auth_sessions
        SET revoked_at = $1
        WHERE user_id = $2 AND revoked_at IS NULL
        """,
        now,
        user_id,
    )

    # All sessions revoked
    rows = await conn.fetch(
        "SELECT revoked_at FROM auth_sessions WHERE user_id = $1", user_id
    )
    assert all(row["revoked_at"] is not None for row in rows)
    assert len(rows) == 3


@pytest.mark.asyncio
async def test_family_id_tracks_rotation_chain(conn):
    """All tokens in a rotation chain share the same family_id."""
    user_id = await _create_user(conn)
    session_id = await _create_session(conn, user_id)
    family_id = uuid.uuid4()

    # Simulate a chain: T1 → T2 → T3
    t1_id, _, _ = await _create_refresh_token(conn, session_id, family_id)
    await _consume_token(conn, t1_id)
    t2_id, _, _ = await _create_refresh_token(conn, session_id, family_id)
    await conn.execute(
        "UPDATE refresh_tokens SET replaced_by_id = $1 WHERE id = $2", t2_id, t1_id
    )

    await _consume_token(conn, t2_id)
    t3_id, _, _ = await _create_refresh_token(conn, session_id, family_id)
    await conn.execute(
        "UPDATE refresh_tokens SET replaced_by_id = $1 WHERE id = $2", t3_id, t2_id
    )

    # All three share the same family_id
    rows = await conn.fetch(
        "SELECT family_id FROM refresh_tokens WHERE family_id = $1", family_id
    )
    assert len(rows) == 3


@pytest.mark.asyncio
async def test_atomic_consume_prevents_double_consumption(pg_refresh_db):
    """Two concurrent connections racing to consume the same token: exactly one wins."""
    conn1 = await asyncpg.connect(pg_refresh_db)
    conn2 = await asyncpg.connect(pg_refresh_db)
    try:
        user_id = await _create_user(conn1, email="racer@example.com")
        session_id = await _create_session(conn1, user_id)
        family_id = uuid.uuid4()
        token_id, _, _ = await _create_refresh_token(conn1, session_id, family_id)

        # Both connections attempt to consume inside serializable transactions
        tx1 = conn1.transaction(isolation="serializable")
        tx2 = conn2.transaction(isolation="serializable")
        await tx1.start()
        await tx2.start()

        now = datetime.now(UTC)
        r1 = await conn1.fetchval(
            """
            UPDATE refresh_tokens
            SET rotated_at = $1
            WHERE id = $2
              AND rotated_at IS NULL
              AND revoked_at IS NULL
              AND expires_at > $1
            RETURNING id
            """,
            now,
            token_id,
        )

        # r1 succeeds (first to commit)
        await tx1.commit()

        r2 = None
        try:
            r2 = await conn2.fetchval(
                """
                UPDATE refresh_tokens
                SET rotated_at = $1
                WHERE id = $2
                  AND rotated_at IS NULL
                  AND revoked_at IS NULL
                  AND expires_at > $1
                RETURNING id
                """,
                now,
                token_id,
            )
            await tx2.commit()
        except asyncpg.SerializationError:
            await tx2.rollback()
            r2 = None

        # Exactly one succeeded
        results = [r1, r2]
        successes = [r for r in results if r is not None]
        assert len(successes) == 1, (
            f"Expected exactly 1 success, got {len(successes)}: {results}"
        )
    finally:
        await conn1.close()
        await conn2.close()


@pytest.mark.asyncio
async def test_self_referential_fk_on_replaced_by_id(conn):
    """The replaced_by_id FK constraint references refresh_tokens.id correctly."""
    user_id = await _create_user(conn)
    session_id = await _create_session(conn, user_id)
    family_id = uuid.uuid4()

    token_id, _, _ = await _create_refresh_token(conn, session_id, family_id)

    # Setting replaced_by_id to a non-existent UUID should fail
    bogus_id = uuid.uuid4()
    with pytest.raises(asyncpg.ForeignKeyViolationError):
        await conn.execute(
            "UPDATE refresh_tokens SET replaced_by_id = $1 WHERE id = $2",
            bogus_id,
            token_id,
        )


@pytest.mark.asyncio
async def test_token_hash_uniqueness(conn):
    """Two tokens cannot share the same token_hash."""
    user_id = await _create_user(conn)
    session_id = await _create_session(conn, user_id)
    family_id = uuid.uuid4()

    raw = _gen_token()
    await _create_refresh_token(conn, session_id, family_id, raw_token=raw)

    with pytest.raises(asyncpg.UniqueViolationError):
        await _create_refresh_token(conn, session_id, family_id, raw_token=raw)


@pytest.mark.asyncio
async def test_cascade_delete_on_session_removal(conn):
    """Deleting an auth_session cascades to its refresh_tokens."""
    user_id = await _create_user(conn)
    session_id = await _create_session(conn, user_id)
    family_id = uuid.uuid4()

    await _create_refresh_token(conn, session_id, family_id)
    await _create_refresh_token(conn, session_id, family_id)

    count_before = await conn.fetchval(
        "SELECT count(*) FROM refresh_tokens WHERE session_id = $1", session_id
    )
    assert count_before == 2

    await conn.execute("DELETE FROM auth_sessions WHERE id = $1", session_id)

    count_after = await conn.fetchval(
        "SELECT count(*) FROM refresh_tokens WHERE session_id = $1", session_id
    )
    assert count_after == 0


@pytest.mark.asyncio
async def test_alembic_migration_0003_upgrade_downgrade_cycle():
    """Verify migration 0003 applies and reverts cleanly via Alembic."""
    cycle_db = "sandeshvani_alembic_0003_test"
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
        await admin_conn.execute(f"CREATE DATABASE {cycle_db};")
    finally:
        await admin_conn.close()

    cycle_dsn = _admin_dsn(PG_TEST_URL, cycle_db)
    sa_url = cycle_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)

    repo_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    env = {
        **os.environ,
        "DATABASE_URL": sa_url,
        "MIGRATION_DATABASE_URL": sa_url,
        "PYTHONPATH": "backend",
    }

    try:
        # 1. Upgrade to 0002 (baseline before 0003)
        res_0002 = subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "-c",
                "backend/alembic.ini",
                "upgrade",
                "0002_secure_role_permissions",
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
            cwd=repo_root,
        )
        assert res_0002.returncode == 0, f"Upgrade to 0002 failed: {res_0002.stderr}"

        # Verify columns do NOT yet exist
        conn = await asyncpg.connect(cycle_dsn)
        try:
            cols_before = await conn.fetch(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'refresh_tokens'
                  AND column_name IN ('rotated_at', 'revoked_at', 'replaced_by_id')
                """
            )
            assert len(cols_before) == 0
        finally:
            await conn.close()

        # 2. Upgrade to 0003 (head)
        res_0003 = subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "-c",
                "backend/alembic.ini",
                "upgrade",
                "0003_refresh_token_lifecycle",
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
            cwd=repo_root,
        )
        assert res_0003.returncode == 0, f"Upgrade to 0003 failed: {res_0003.stderr}"

        # Verify all 3 columns and foreign key now exist
        conn = await asyncpg.connect(cycle_dsn)
        try:
            cols_after = await conn.fetch(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'refresh_tokens'
                  AND column_name IN ('rotated_at', 'revoked_at', 'replaced_by_id')
                """
            )
            assert len(cols_after) == 3

            fk_check = await conn.fetchval(
                """
                SELECT conname
                FROM pg_constraint
                WHERE conname = 'fk_refresh_tokens_replaced_by'
                """
            )
            assert fk_check == "fk_refresh_tokens_replaced_by"
        finally:
            await conn.close()

        # 3. Downgrade back to 0002
        res_down = subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "-c",
                "backend/alembic.ini",
                "downgrade",
                "0002_secure_role_permissions",
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
            cwd=repo_root,
        )
        assert res_down.returncode == 0, f"Downgrade to 0002 failed: {res_down.stderr}"

        # Verify columns were removed
        conn = await asyncpg.connect(cycle_dsn)
        try:
            cols_reverted = await conn.fetch(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'refresh_tokens'
                  AND column_name IN ('rotated_at', 'revoked_at', 'replaced_by_id')
                """
            )
            assert len(cols_reverted) == 0
        finally:
            await conn.close()

        # 4. Clean downgrade to base
        res_base = subprocess.run(
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
            cwd=repo_root,
        )
        assert res_base.returncode == 0, f"Downgrade to base failed: {res_base.stderr}"

    finally:
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

