"""End-to-end PostgreSQL API tests for tenant RLS transaction boundaries.

These tests deliberately run the real Alembic history and the FastAPI endpoints
as a restricted, non-owner, NOBYPASSRLS application role. They are skipped when
SANDESHVANI_PG_TEST_URL is not configured.
"""

from __future__ import annotations

import os
import secrets
import subprocess
import sys
import uuid
from pathlib import Path

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.main import create_app
from app.models.audience_member import AudienceMember

PG_TEST_URL = os.environ.get("SANDESHVANI_PG_TEST_URL", "")
if not PG_TEST_URL:
    pytest.skip(
        "SANDESHVANI_PG_TEST_URL not set; PostgreSQL API RLS tests are skipped",
        allow_module_level=True,
    )

pytest.importorskip("asyncpg")
BACKEND_DIR = Path(__file__).resolve().parents[1]


def _url_for(database_url: str, *, database: str, driver: str, username=None, password=None):
    url = make_url(database_url).set(drivername=driver, database=database)
    if username is not None:
        url = url.set(username=username, password=password)
    return url.render_as_string(hide_password=False)


@pytest.fixture
async def pg_api_runtime(tmp_path):
    """Migrate a disposable database and expose only a restricted app DSN."""
    database = f"sv_api_rls_{uuid.uuid4().hex[:12]}"
    role = f"sv_api_app_{uuid.uuid4().hex[:10]}"
    password = secrets.token_hex(24)
    admin_dsn = _url_for(
        PG_TEST_URL,
        database=make_url(PG_TEST_URL).database or "postgres",
        driver="postgresql",
    )
    admin = await asyncpg.connect(admin_dsn)
    try:
        await admin.execute(
            f"CREATE ROLE {role} LOGIN PASSWORD '{password}' "
            "NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE"
        )
        await admin.execute(f"CREATE DATABASE {database}")
    finally:
        await admin.close()

    migration_url = _url_for(
        PG_TEST_URL,
        database=database,
        driver="postgresql+asyncpg",
    )
    runtime_url = _url_for(
        PG_TEST_URL,
        database=database,
        driver="postgresql+asyncpg",
        username=role,
        password=password,
    )
    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "local",
            "DEPLOYMENT_ENVIRONMENT": "development",
            "MIGRATION_DATABASE_URL": migration_url,
            "MIGRATION_DATABASE_ROLE": "",
            "PYTHONPATH": str(BACKEND_DIR),
        }
    )
    migration = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env,
        text=True,
        capture_output=True,
        timeout=180,
        check=False,
    )
    assert migration.returncode == 0, (
        "Alembic upgrade head failed:\n"
        f"STDOUT:\n{migration.stdout}\nSTDERR:\n{migration.stderr}"
    )

    app_admin = await asyncpg.connect(
        _url_for(PG_TEST_URL, database=database, driver="postgresql")
    )
    try:
        await app_admin.execute(f"GRANT CONNECT ON DATABASE {database} TO {role}")
        await app_admin.execute(f"GRANT USAGE ON SCHEMA public TO {role}")
        await app_admin.execute(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {role}"
        )
        await app_admin.execute(
            f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {role}"
        )
        role_flags = await app_admin.fetchrow(
            "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = $1",
            role,
        )
        assert role_flags is not None
        assert role_flags["rolsuper"] is False
        assert role_flags["rolbypassrls"] is False
        owner_count = await app_admin.fetchval(
            """
            SELECT count(*)
            FROM pg_class c
            JOIN pg_roles r ON r.oid = c.relowner
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relname IN (
                'memberships', 'membership_roles', 'roles',
                'audience_members', 'audience_import_uploads',
                'audience_import_jobs', 'outbox_events'
              )
              AND r.rolname = $1
            """,
            role,
        )
        assert owner_count == 0, "The runtime role must not own tenant-protected tables"
    finally:
        await app_admin.close()

    engine = create_async_engine(runtime_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    settings = Settings(
        _env_file=None,
        app_env="local",
        deployment_environment="development",
        enable_local_mail_sink=True,
        database_url=runtime_url,
        audience_import_storage_dir=tmp_path / "private-imports",
    )
    try:
        yield {
            "database": database,
            "role": role,
            "runtime_url": runtime_url,
            "engine": engine,
            "factory": factory,
            "settings": settings,
            "storage": settings.audience_import_storage_dir,
        }
    finally:
        await engine.dispose()
        teardown = await asyncpg.connect(admin_dsn)
        try:
            await teardown.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = $1 AND pid <> pg_backend_pid()",
                database,
            )
            await teardown.execute(f"DROP DATABASE IF EXISTS {database}")
            await teardown.execute(f"DROP ROLE IF EXISTS {role}")
        finally:
            await teardown.close()


async def _register_and_verify(
    client: AsyncClient,
    app,
    email: str,
    *,
    password: str = "PostgresApiPassword123!",
) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Postgres API User"},
    )
    assert response.status_code == 201, response.text
    message = app.state.development_mail_sink.consume_latest(
        email, "email-verification"
    )
    assert message is not None and message.token
    verified = await client.post(
        "/api/v1/auth/verify-email", json={"token": message.token}
    )
    assert verified.status_code == 200, verified.text


@pytest.mark.asyncio
async def test_audience_create_update_upload_and_member_role_response_under_postgres_rls(
    pg_api_runtime,
):
    runtime = pg_api_runtime
    settings = runtime["settings"]
    app = create_app(settings)
    app.state.development_mail_sink.clear()
    app.state.auth_login_rate_limiter.clear()
    app.state.auth_recovery_rate_limiter.clear()

    async def override_get_db():
        async with runtime["factory"]() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: settings

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Origin": "http://localhost:5173"},
    ) as client:
        await _register_and_verify(client, app, "rls-owner@example.test")
        login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "rls-owner@example.test",
                "password": "PostgresApiPassword123!",
            },
        )
        assert login.status_code == 200, login.text
        access_token = login.json()["access_token"]
        csrf_token = login.json()["csrf_token"]
        org_response = await client.post(
            "/api/v1/organizations",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"name": "Postgres RLS Test", "slug": f"rls-{uuid.uuid4().hex[:10]}"},
        )
        assert org_response.status_code == 201, org_response.text
        organization_id = org_response.json()["id"]

        switched = await client.post(
            "/api/v1/auth/select-org",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"organization_id": organization_id},
        )
        assert switched.status_code == 200, switched.text
        access_token = switched.json()["access_token"]

        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Organization-ID": organization_id,
            "X-CSRF-Token": csrf_token,
        }

        created = await client.post(
            "/api/v1/audiences",
            headers=headers,
            json={
                "full_name": "Asha RLS",
                "email": "asha.rls@example.test",
                "preferred_language": "hi",
                "state_code": "IN-UP",
                "city": "Meerut",
            },
        )
        assert created.status_code == 201, created.text
        member_id = created.json()["id"]
        assert created.json()["state_code"] == "IN-UP"
        assert created.json()["city"] == "Meerut"

        updated = await client.patch(
            f"/api/v1/audiences/{member_id}",
            headers=headers,
            json={"city": "Lucknow", "district": "Lucknow"},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["city"] == "Lucknow"

        role_response = await client.get(
            f"/api/v1/organizations/{organization_id}/roles",
            headers=headers,
        )
        assert role_response.status_code == 200, role_response.text
        campaign_manager = next(
            role for role in role_response.json() if role["name"] == "Campaign Manager"
        )

        await _register_and_verify(client, app, "rls-invitee@example.test")
        added = await client.post(
            f"/api/v1/organizations/{organization_id}/members",
            headers=headers,
            json={
                "email": "rls-invitee@example.test",
                "role_ids": [campaign_manager["id"]],
            },
        )
        assert added.status_code == 201, added.text
        assert [role["name"] for role in added.json()["roles"]] == ["Campaign Manager"]

        csv_body = (
            b"full_name,email,state_code,city\r\n"
            b"Import RLS,import.rls@example.test,IN-UP,Meerut\\r\\n"
        )
        upload = await client.post(
            "/api/v1/audiences/imports",
            headers=headers,
            files={"file": ("rls-contacts.csv", csv_body, "text/csv")},
        )
        assert upload.status_code == 202, upload.text
        assert upload.json()["job_id"]
        assert upload.json()["status"] == "queued"
        stored_files = list(runtime["storage"].glob("*.csv"))
        assert len(stored_files) == 1

        # RLS must fail closed on a fresh transaction without app.current_org.
        async with runtime["factory"]() as session:
            invisible = await session.scalars(select(AudienceMember))
            assert list(invisible) == []

    app.dependency_overrides.clear()
