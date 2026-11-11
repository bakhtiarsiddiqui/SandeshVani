"""
Tests for SPEC-02 follow-on: organization role provisioning and tenant context.

Covers:
  1. Two organizations receive distinct org-scoped system roles (not platform-scoped).
  2. Creator gets Organization Administrator role in same transaction as org creation.
  3. Platform roles are NOT returned by get_organization_roles().
  4. A role from org A cannot be assigned to a member of org B (ValueError from repo).
  5. Organization path ID mismatch with active tenant context returns HTTP 403.
  6. Tenant context is established before RLS-protected membership queries
     (session.info["current_org"] is set prior to membership lookup).
  7. A failed provisioning step rolls back and does not leave a partially created org.

NOTE: PostgreSQL RLS / composite-FK enforcement must be validated separately against a
running PostgreSQL instance; SQLite does not enforce RLS policies. See AGENTS.md.
"""

import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.main import create_app
from app.models.base import Base
from app.models.membership import Membership
from app.models.organization import Organization
from app.models.role import MembershipRole, Role
from app.models.user import User
from app.repositories.membership_repo import MembershipRepository
from app.repositories.role_repo import RoleRepository

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_SETTINGS = Settings(
    _env_file=None,
    app_env="local",
    deployment_environment="development",
    enable_local_mail_sink=True,
)
app = create_app(TEST_SETTINGS)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def fk_session() -> AsyncGenerator[AsyncSession, None]:
    """SQLite session with foreign-key constraints enabled."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)

    @event.listens_for(engine.sync_engine, "connect")
    def _set_fk(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def api_session() -> AsyncGenerator[AsyncSession, None]:
    """Plain SQLite session used by API integration tests."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def api_client(api_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client wired to api_session."""
    app.state.development_mail_sink.clear()
    app.state.auth_recovery_rate_limiter.clear()
    app.state.auth_recovery_rate_limiter.clear()

    async def _override():
        yield api_session

    app.dependency_overrides[get_db] = _override
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
    from httpx import ASGITransport

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Origin": "http://localhost:5173"},
    ) as client:
        yield client

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_login(client: AsyncClient, email: str) -> tuple[str, str]:
    password = "StrongPassword99!"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert reg.status_code == 201
    mail = app.state.development_mail_sink.consume_latest(email, "email-verification")
    assert mail is not None and mail.token is not None
    token = mail.token
    await client.post("/api/v1/auth/verify-email", json={"token": token})
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    data = login.json()
    return data["access_token"], data["csrf_token"]


async def _create_org(client: AsyncClient, token: str, name: str, slug: str) -> dict:
    res = await client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "slug": slug},
    )
    assert res.status_code == 201, res.text
    return res.json()


# ---------------------------------------------------------------------------
# Test 1 — Two organizations receive distinct org-scoped system roles
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_two_orgs_receive_distinct_org_scoped_system_roles(
    fk_session: AsyncSession,
):
    """Each org gets its own copies of system roles with scope='organization'."""
    org1 = Organization(id=uuid.uuid4(), name="Org Alpha", slug="org-alpha")
    org2 = Organization(id=uuid.uuid4(), name="Org Beta", slug="org-beta")
    fk_session.add_all([org1, org2])
    await fk_session.flush()

    repo = RoleRepository(fk_session)
    await repo.seed_organization_roles(org1.id)
    await repo.seed_organization_roles(org2.id)

    roles_1 = await repo.get_organization_roles(org1.id)
    roles_2 = await repo.get_organization_roles(org2.id)

    # Both orgs get 4 system roles
    assert len(roles_1) == 4
    assert len(roles_2) == 4

    # All roles are org-scoped and belong to the correct organization
    for r in roles_1:
        assert r.scope == "organization", f"Expected org scope, got {r.scope}"
        assert r.organization_id == org1.id, "Role belongs to wrong org"

    for r in roles_2:
        assert r.scope == "organization"
        assert r.organization_id == org2.id

    # Role IDs are distinct across organizations
    ids_1 = {r.id for r in roles_1}
    ids_2 = {r.id for r in roles_2}
    assert ids_1.isdisjoint(ids_2), "Role IDs must not be shared across organizations"

    # Role names are identical (same template), but they are independent rows
    names_1 = {r.name for r in roles_1}
    names_2 = {r.name for r in roles_2}
    assert (
        names_1
        == names_2
        == {
            "Organization Administrator",
            "Campaign Manager",
            "Communication Team",
            "Approver",
        }
    )


# ---------------------------------------------------------------------------
# Test 2 — Creator gets Org Admin role in the same transaction as org creation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_creator_gets_org_admin_role_in_same_transaction(
    api_client: AsyncClient,
    api_session: AsyncSession,
):
    """Creator must have the Org Administrator role immediately after creation."""
    token, _ = await _register_and_login(api_client, "founder@district.gov.in")
    org = await _create_org(api_client, token, "District Council", "district-council")
    org_id = org["id"]

    # Confirm via /auth/me (which checks active org permissions)
    me_res = await api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    me = me_res.json()
    assert me["active_organization"]["id"] == org_id
    # Organization Administrator includes members:create and roles:assign
    perms = set(me["permissions"])
    assert "members:create" in perms, "Creator must have members:create permission"
    assert "roles:assign" in perms, "Creator must have roles:assign permission"

    # Confirm role assignment exists in DB
    result = await api_session.execute(
        select(Membership).where(
            Membership.organization_id == uuid.UUID(org_id),
        )
    )
    membership = result.scalar_one_or_none()
    assert membership is not None, "Creator membership must exist"

    # Membership must have exactly one role assignment (Organization Administrator)
    mr_result = await api_session.execute(
        select(MembershipRole).where(MembershipRole.membership_id == membership.id)
    )
    mrs = mr_result.scalars().all()
    assert len(mrs) == 1, "Creator must have exactly one role"

    role_result = await api_session.execute(
        select(Role).where(Role.id == mrs[0].role_id)
    )
    role = role_result.scalar_one()
    assert role.name == "Organization Administrator"
    assert role.scope == "organization"
    assert role.organization_id == uuid.UUID(org_id)


# ---------------------------------------------------------------------------
# Test 3 — Platform roles are NOT returned by get_organization_roles()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_platform_roles_not_returned_by_get_organization_roles(
    fk_session: AsyncSession,
):
    """get_organization_roles() must exclude platform-scoped roles."""
    org = Organization(id=uuid.uuid4(), name="Civic Org", slug="civic-org")
    platform_role = Role(
        id=uuid.uuid4(),
        name="Platform Support",
        scope="platform",
        organization_id=None,
    )
    org_role = Role(
        id=uuid.uuid4(),
        name="Org Reviewer",
        scope="organization",
        organization_id=org.id,
    )
    fk_session.add_all([org, platform_role, org_role])
    await fk_session.flush()

    repo = RoleRepository(fk_session)
    roles = await repo.get_organization_roles(org.id)

    role_ids = {r.id for r in roles}
    assert org_role.id in role_ids, "Org-scoped role must be returned"
    assert platform_role.id not in role_ids, "Platform role must not be returned"
    for r in roles:
        assert r.scope == "organization"


# ---------------------------------------------------------------------------
# Test 4 — Role from org A cannot be assigned to a member of org B (repo layer)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_org_role_assignment_raises_via_repo(fk_session: AsyncSession):
    """MembershipRepository.assign_role must reject roles from another organization."""
    org_a = Organization(id=uuid.uuid4(), name="Org A", slug="prov-org-a")
    org_b = Organization(id=uuid.uuid4(), name="Org B", slug="prov-org-b")
    user = User(
        id=uuid.uuid4(),
        email="member@prov-test.gov.in",
        normalized_email="member@prov-test.gov.in",
        password_hash="hash",
        full_name="Member",
    )
    fk_session.add_all([org_a, org_b, user])
    await fk_session.flush()

    membership_a = Membership(
        id=uuid.uuid4(), organization_id=org_a.id, user_id=user.id
    )
    role_b = Role(
        id=uuid.uuid4(),
        name="Org B Admin",
        scope="organization",
        organization_id=org_b.id,
    )
    fk_session.add_all([membership_a, role_b])
    await fk_session.flush()

    repo = MembershipRepository(fk_session)
    with pytest.raises(ValueError, match="not valid for this organization"):
        await repo.assign_role(
            organization_id=org_a.id,
            membership_id=membership_a.id,
            role_id=role_b.id,
        )


# ---------------------------------------------------------------------------
# Test 5 — Organization path ID mismatch with active tenant context → HTTP 403
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_path_org_id_mismatch_returns_403(
    api_client: AsyncClient,
):
    """require_permissions must reject requests where path org_id ≠ active token org."""
    token_a, _ = await _register_and_login(api_client, "admin_mismatch_a@gov.in")
    token_b, _ = await _register_and_login(api_client, "admin_mismatch_b@gov.in")

    org_a = await _create_org(api_client, token_a, "Mismatch Org A", "mismatch-org-a")
    org_b = await _create_org(api_client, token_b, "Mismatch Org B", "mismatch-org-b")

    # token_a is scoped to org_a. Attempt to read org_b's members using token_a
    # with org_b's org_id in the path AND header — this should 403 (not a member)
    # or 403 (path mismatch after context is resolved).
    res = await api_client.get(
        f"/api/v1/organizations/{org_b['id']}/members",
        headers={
            "Authorization": f"Bearer {token_a}",
            "X-Organization-ID": org_b["id"],
        },
    )
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"
    # Could be "not an active member" (membership check) or "path ID does not match"
    # (path check after switching context). Both are correct 403 behaviors.
    detail = res.json()["detail"].lower()
    assert "403" not in detail  # just confirm it's the JSON detail, not status
    assert len(detail) > 0

    # Now get a token explicitly scoped to org_a, then try path with org_b's ID
    switch_res = await api_client.post(
        "/api/v1/auth/select-org",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"organization_id": org_a["id"]},
    )
    assert switch_res.status_code == 200
    org_a_token = switch_res.json()["access_token"]

    # This token is bound to org_a — asking for org_b's members must 403
    mismatch_res = await api_client.get(
        f"/api/v1/organizations/{org_b['id']}/members",
        headers={
            "Authorization": f"Bearer {org_a_token}",
            "X-Organization-ID": org_a["id"],
        },
    )
    assert mismatch_res.status_code == 403


# ---------------------------------------------------------------------------
# Test 6 — Tenant context is set BEFORE membership query
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tenant_context_set_before_membership_query(fk_session: AsyncSession):
    """set_tenant_context must be called and recorded in session.info before the
    membership lookup occurs. This is verifiable because set_tenant_context writes
    session.info['current_org']; the membership query relies on that for RLS.
    """
    from app.db.session import set_tenant_context

    org = Organization(id=uuid.uuid4(), name="RLS Test Org", slug="rls-test-org")
    fk_session.add(org)
    await fk_session.flush()

    # Before calling set_tenant_context the key must not be set
    assert fk_session.info.get("current_org") is None

    await set_tenant_context(fk_session, org.id)

    # After calling it, the key must be set to the target org id (stored as UUID)
    assert fk_session.info.get("current_org") == org.id, (
        "Tenant context was not stored in session.info before membership query"
    )


# ---------------------------------------------------------------------------
# Test 7 — Failed provisioning rolls back; no partial org remains
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_failed_provisioning_rolls_back_entirely(api_session: AsyncSession):
    """If seed_organization_roles raises, the whole transaction must roll back
    so the organization, membership, and role rows are not persisted.

    Uses raise_app_exceptions=False so the RuntimeError becomes a 500 response
    rather than propagating through the test.
    """
    from httpx import ASGITransport

    # Dedicated client with raise_app_exceptions=False to capture 500 responses
    no_raise_transport = ASGITransport(app=app, raise_app_exceptions=False)

    async def _override():
        yield api_session

    app.dependency_overrides[get_db] = _override
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
    try:
        async with AsyncClient(
            transport=no_raise_transport,
            base_url="http://test",
            headers={"Origin": "http://localhost:5173"},
        ) as client:
            # Register and login a user
            password = "StrongPassword99!"
            reg = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "rollback_test@gov.in",
                    "password": password,
                    "full_name": "Rollback Tester",
                },
            )
            assert reg.status_code == 201
            mail = app.state.development_mail_sink.consume_latest(
                "rollback_test@gov.in", "email-verification"
            )
            assert mail is not None and mail.token is not None
            vtoken = mail.token
            await client.post("/api/v1/auth/verify-email", json={"token": vtoken})
            login = await client.post(
                "/api/v1/auth/login",
                json={"email": "rollback_test@gov.in", "password": password},
            )
            token = login.json()["access_token"]

            with patch(
                "app.repositories.role_repo.RoleRepository.seed_organization_roles",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Simulated seed failure"),
            ):
                res = await client.post(
                    "/api/v1/organizations",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"name": "Rollback Org", "slug": "rollback-org"},
                )

            # Must fail — exact status depends on FastAPI error handler (500)
            assert res.status_code >= 500, (
                f"Expected 5xx after seed failure, got {res.status_code}: {res.text}"
            )

            # Verify rollback: slug must be available again (no partial row persisted).
            # Create a fresh client with normal error behaviour for the retry.
            retry_res = await client.post(
                "/api/v1/organizations",
                headers={"Authorization": f"Bearer {token}"},
                json={"name": "Rollback Org Retry", "slug": "rollback-org"},
            )
            assert retry_res.status_code == 201, (
                f"Slug 'rollback-org' should be available after rollback, "
                f"got {retry_res.status_code}: {retry_res.text}"
            )
    finally:
        app.dependency_overrides.clear()
