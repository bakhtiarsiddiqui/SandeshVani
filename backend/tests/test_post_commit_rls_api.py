"""PostgreSQL API regression test for transaction-local tenant RLS.

This test migrates a disposable database, grants the API a restricted runtime
role, and exercises the endpoints that used to refresh/query ORM rows after
COMMIT had cleared app.current_org.
"""

from __future__ import annotations

import os
import secrets
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.deps import AuthContext, get_current_user, verify_csrf
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.main import create_app
from app.models.user import User
from app.services.organization_service import OrganizationService

PG_TEST_URL = os.environ.get("SANDESHVANI_PG_TEST_URL", "")
if not PG_TEST_URL:
    pytest.skip(
        "SANDESHVANI_PG_TEST_URL not set — skipping PostgreSQL API/RLS test",
        allow_module_level=True,
    )


def _url_for_database(
    database: str,
    *,
    username: str | None = None,
    password: str | None = None,
    async_driver: bool = False,
) -> str:
    url = make_url(PG_TEST_URL)
    return url.set(
        drivername="postgresql+asyncpg" if async_driver else "postgresql",
        database=database,
        username=username if username is not None else url.username,
        password=password if password is not None else url.password,
    ).render_as_string(hide_password=False)


@pytest.fixture
async def postgres_api_environment(tmp_path):
    """Run current Alembic migrations and expose a non-owner API DB role."""
    suffix = secrets.token_hex(5)
    database = f"sv_api_rls_{suffix}"
    app_role = f"sv_api_app_{suffix}"
    app_password = secrets.token_urlsafe(24)
    admin_url = make_url(PG_TEST_URL)
    admin_dsn = admin_url.render_as_string(hide_password=False)

    admin = await asyncpg.connect(admin_dsn)
    try:
        await admin.execute(
            f"CREATE ROLE \"{app_role}\" LOGIN PASSWORD '{app_password}' "
            "NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;"
        )
        await admin.execute(f'CREATE DATABASE "{database}";')
    finally:
        await admin.close()

    db_admin_async_url = _url_for_database(database, async_driver=True)
    backend_dir = Path(__file__).resolve().parents[1]
    migration_env = os.environ.copy()
    migration_env.update(
        {
            "MIGRATION_DATABASE_URL": db_admin_async_url,
            "MIGRATION_DATABASE_ROLE": "",
            "APP_ENV": "local",
            "DEPLOYMENT_ENVIRONMENT": "development",
            "PYTHONPATH": str(backend_dir),
        }
    )
    migration = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=backend_dir,
        env=migration_env,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    if migration.returncode != 0:
        raise AssertionError(
            "Disposable PostgreSQL Alembic upgrade failed:\n"
            f"{migration.stdout}\n{migration.stderr}"
        )

    admin_test = await asyncpg.connect(_url_for_database(database))
    try:
        await admin_test.execute(f'GRANT USAGE ON SCHEMA public TO "{app_role}";')
        await admin_test.execute(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public "
            f'TO "{app_role}";'
        )
        await admin_test.execute(
            f"GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public "
            f'TO "{app_role}";'
        )
    finally:
        await admin_test.close()

    runtime_url = _url_for_database(
        database,
        username=app_role,
        password=app_password,
        async_driver=True,
    )
    admin_async_url = _url_for_database(database, async_driver=True)
    engine = create_async_engine(runtime_url, pool_pre_ping=True)
    admin_engine = create_async_engine(admin_async_url, pool_pre_ping=True)
    app_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    admin_factory = async_sessionmaker(
        admin_engine, expire_on_commit=False, autoflush=False
    )

    try:
        async with admin_factory() as session:
            actor = User(
                email=f"rls-admin-{suffix}@example.com",
                normalized_email=f"rls-admin-{suffix}@example.com",
                password_hash="unused-in-this-api-test",
                full_name="RLS API Administrator",
                status="active",
            )
            invitee = User(
                email=f"rls-invitee-{suffix}@example.com",
                normalized_email=f"rls-invitee-{suffix}@example.com",
                password_hash="unused-in-this-api-test",
                full_name="RLS API Invitee",
                status="active",
            )
            session.add_all([actor, invitee])
            await session.flush()
            organization = await OrganizationService(session).create_organization(
                name="RLS API Test Organization",
                slug=f"rls-api-{suffix}",
                creator_user_id=actor.id,
            )
            # OrganizationService commits provisioning; query the selected role
            # in a fresh owner session for assignment through the API.
            from app.repositories.role_repo import RoleRepository

            roles = await RoleRepository(session).get_organization_roles(
                organization.id
            )
            campaign_manager = next(
                role for role in roles if role.name == "Campaign Manager"
            )
            await session.commit()
            actor_id = actor.id
            invitee_email = invitee.email
            organization_id = organization.id
            role_id = campaign_manager.id

        yield {
            "app_factory": app_factory,
            "actor_id": actor_id,
            "invitee_email": invitee_email,
            "organization_id": organization_id,
            "role_id": role_id,
            "tmp_path": tmp_path,
        }
    finally:
        await engine.dispose()
        await admin_engine.dispose()
        cleanup = await asyncpg.connect(admin_dsn)
        try:
            await cleanup.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = $1 AND pid <> pg_backend_pid()",
                database,
            )
            await cleanup.execute(f'DROP DATABASE IF EXISTS "{database}";')
            await cleanup.execute(f'DROP ROLE IF EXISTS "{app_role}";')
        finally:
            await cleanup.close()


@pytest.mark.asyncio
async def test_audience_and_member_api_responses_keep_rls_tenant_context(
    postgres_api_environment,
):
    settings = Settings(
        _env_file=None,
        app_env="local",
        deployment_environment="development",
        enable_local_mail_sink=True,
        allowed_origins=["http://localhost:5173"],
        audience_import_storage_dir=postgres_api_environment["tmp_path"] / "uploads",
    )
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db] = None

    async def override_db():
        async with postgres_api_environment["app_factory"]() as session:
            yield session

    auth_ctx = AuthContext(
        user=SimpleNamespace(id=postgres_api_environment["actor_id"]),
        session_id=__import__("uuid").uuid4(),
        org_id=postgres_api_environment["organization_id"],
    )

    async def override_user():
        return auth_ctx

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[verify_csrf] = lambda: None

    headers = {
        "Authorization": "Bearer test-only-auth-context",
        "X-Organization-ID": str(postgres_api_environment["organization_id"]),
    }
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={**headers, "Origin": "http://localhost:5173"},
    ) as client:
        created = await client.post(
            "/api/v1/audiences",
            json={
                "full_name": "Post Commit RLS Test",
                "email": "post-commit@example.com",
                "preferred_language": "en",
            },
        )
        assert created.status_code == 201, created.text
        member_id = created.json()["id"]

        updated = await client.patch(
            f"/api/v1/audiences/{member_id}",
            json={"full_name": "Post Commit RLS Updated"},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["full_name"] == "Post Commit RLS Updated"

        upload = await client.post(
            "/api/v1/audiences/imports",
            files={
                "file": (
                    "rls-audience.csv",
                    "full_name,email\nCSV RLS Test,csv-rls@example.com\n",
                    "text/csv",
                )
            },
        )
        assert upload.status_code == 202, upload.text
        job_id = upload.json()["job_id"]
        job = await client.get(f"/api/v1/audiences/imports/{job_id}")
        assert job.status_code == 200, job.text

        added = await client.post(
            f"/api/v1/organizations/{postgres_api_environment['organization_id']}/members",
            json={
                "email": postgres_api_environment["invitee_email"],
                "role_ids": [str(postgres_api_environment["role_id"])],
            },
        )
        assert added.status_code == 201, added.text
        payload = added.json()
        assert payload["user"]["email"] == postgres_api_environment["invitee_email"]
        assert any(
            role["id"] == str(postgres_api_environment["role_id"])
            for role in payload["roles"]
        )
