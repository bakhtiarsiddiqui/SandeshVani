import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import selectinload

from app.models.base import Base
from app.models.membership import Membership
from app.models.organization import Organization
from app.models.role import (
    MembershipRole,
    Permission,
    PlatformRoleAssignment,
    Role,
    RolePermission,
)
from app.models.user import User
from app.repositories.role_repo import RoleRepository

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def fk_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Test session with foreign key constraints explicitly enabled in SQLite."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_organization_role_requires_non_null_organization_id(
    fk_db_session: AsyncSession,
):
    """1. An organization role cannot have a null organization ID."""
    role = Role(
        id=uuid.uuid4(),
        name="Org Admin",
        scope="organization",
        organization_id=None,
    )
    fk_db_session.add(role)
    with pytest.raises(IntegrityError):
        await fk_db_session.flush()


@pytest.mark.asyncio
async def test_platform_role_requires_null_organization_id(
    fk_db_session: AsyncSession,
):
    """2. A platform role cannot have an organization ID."""
    org_id = uuid.uuid4()
    role = Role(
        id=uuid.uuid4(),
        name="Platform Admin",
        scope="platform",
        organization_id=org_id,
    )
    fk_db_session.add(role)
    with pytest.raises(IntegrityError):
        await fk_db_session.flush()


@pytest.mark.asyncio
async def test_duplicate_role_names_differing_only_by_case_rejected_in_same_scope(
    fk_db_session: AsyncSession,
):
    """3. Duplicate role names differing by case are rejected in the same scope."""
    org = Organization(id=uuid.uuid4(), name="Org Meerut", slug="org-meerut")
    fk_db_session.add(org)
    await fk_db_session.flush()

    # 3a. Organization scope collision
    r1 = Role(
        id=uuid.uuid4(),
        name="Auditor",
        scope="organization",
        organization_id=org.id,
    )
    fk_db_session.add(r1)
    await fk_db_session.flush()

    r2 = Role(
        id=uuid.uuid4(),
        name="auditor",
        scope="organization",
        organization_id=org.id,
    )
    fk_db_session.add(r2)
    with pytest.raises(IntegrityError):
        await fk_db_session.flush()

    await fk_db_session.rollback()

    # 3b. Platform scope collision
    p1 = Role(
        id=uuid.uuid4(),
        name="Global Supervisor",
        scope="platform",
        organization_id=None,
    )
    fk_db_session.add(p1)
    await fk_db_session.flush()

    p2 = Role(
        id=uuid.uuid4(),
        name="global supervisor",
        scope="platform",
        organization_id=None,
    )
    fk_db_session.add(p2)
    with pytest.raises(IntegrityError):
        await fk_db_session.flush()


@pytest.mark.asyncio
async def test_same_role_name_permitted_across_different_organizations(
    fk_db_session: AsyncSession,
):
    """4. The same organization role name can exist in different organizations."""
    org1 = Organization(id=uuid.uuid4(), name="Dept Health", slug="dept-health")
    org2 = Organization(id=uuid.uuid4(), name="Dept Education", slug="dept-edu")
    fk_db_session.add_all([org1, org2])
    await fk_db_session.flush()

    r1 = Role(
        id=uuid.uuid4(),
        name="Manager",
        scope="organization",
        organization_id=org1.id,
    )
    r2 = Role(
        id=uuid.uuid4(),
        name="manager",  # Case variant across different orgs is valid
        scope="organization",
        organization_id=org2.id,
    )
    fk_db_session.add_all([r1, r2])
    await fk_db_session.flush()

    roles = (
        (
            await fk_db_session.execute(
                select(Role).where(Role.id.in_([r1.id, r2.id]))
            )
        )
        .scalars()
        .all()
    )
    assert len(roles) == 2


@pytest.mark.asyncio
async def test_membership_cannot_be_assigned_another_organization_role(
    fk_db_session: AsyncSession,
):
    """5. A membership cannot be assigned another organization's role."""
    org_a = Organization(id=uuid.uuid4(), name="Org A", slug="org-a")
    org_b = Organization(id=uuid.uuid4(), name="Org B", slug="org-b")
    user = User(
        id=uuid.uuid4(),
        email="user_a@test.gov.in",
        normalized_email="user_a@test.gov.in",
        password_hash="secret",
        full_name="User A",
    )
    fk_db_session.add_all([org_a, org_b, user])
    await fk_db_session.flush()

    membership_a = Membership(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        user_id=user.id,
    )
    role_b = Role(
        id=uuid.uuid4(),
        name="Org B Officer",
        scope="organization",
        organization_id=org_b.id,
    )
    fk_db_session.add_all([membership_a, role_b])
    await fk_db_session.flush()

    # Attempt cross-tenant assignment: membership in org_a, role in org_b
    invalid_mr = MembershipRole(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        membership_id=membership_a.id,
        role_id=role_b.id,
    )
    fk_db_session.add(invalid_mr)
    with pytest.raises(IntegrityError):
        await fk_db_session.flush()


@pytest.mark.asyncio
async def test_membership_cannot_be_assigned_platform_role(
    fk_db_session: AsyncSession,
):
    """6. A membership cannot be assigned a platform role."""
    org = Organization(id=uuid.uuid4(), name="Org X", slug="org-x")
    user = User(
        id=uuid.uuid4(),
        email="user_x@test.gov.in",
        normalized_email="user_x@test.gov.in",
        password_hash="secret",
        full_name="User X",
    )
    platform_role = Role(
        id=uuid.uuid4(),
        name="Platform Auditor",
        scope="platform",
        organization_id=None,
    )
    fk_db_session.add_all([org, user, platform_role])
    await fk_db_session.flush()

    membership = Membership(
        id=uuid.uuid4(),
        organization_id=org.id,
        user_id=user.id,
    )
    fk_db_session.add(membership)
    await fk_db_session.flush()

    # Attempt to assign platform role to membership
    invalid_mr = MembershipRole(
        id=uuid.uuid4(),
        organization_id=org.id,
        membership_id=membership.id,
        role_id=platform_role.id,
    )
    fk_db_session.add(invalid_mr)
    with pytest.raises(IntegrityError):
        await fk_db_session.flush()


@pytest.mark.asyncio
async def test_platform_assignment_cannot_reference_organization_role(
    fk_db_session: AsyncSession,
):
    """7. A platform assignment cannot reference an organization role."""
    org = Organization(id=uuid.uuid4(), name="Org Y", slug="org-y")
    user = User(
        id=uuid.uuid4(),
        email="user_y@test.gov.in",
        normalized_email="user_y@test.gov.in",
        password_hash="secret",
        full_name="User Y",
    )
    org_role = Role(
        id=uuid.uuid4(),
        name="Org Y Local Role",
        scope="organization",
        organization_id=org.id,
    )
    fk_db_session.add_all([org, user, org_role])
    await fk_db_session.flush()

    # Attempt to assign organization role as a platform role assignment
    invalid_pa = PlatformRoleAssignment(
        id=uuid.uuid4(),
        user_id=user.id,
        role_scope="platform",
        role_id=org_role.id,
    )
    fk_db_session.add(invalid_pa)
    with pytest.raises(IntegrityError):
        await fk_db_session.flush()


@pytest.mark.asyncio
async def test_platform_role_can_be_assigned_through_platform_role_assignment(
    fk_db_session: AsyncSession,
):
    """8. A platform role can be assigned through PlatformRoleAssignment."""
    user = User(
        id=uuid.uuid4(),
        email="operator@platform.internal",
        normalized_email="operator@platform.internal",
        password_hash="secret",
        full_name="Platform Operator",
    )
    platform_role = Role(
        id=uuid.uuid4(),
        name="Platform Operator",
        scope="platform",
        organization_id=None,
    )
    fk_db_session.add_all([user, platform_role])
    await fk_db_session.flush()

    pa = PlatformRoleAssignment(
        id=uuid.uuid4(),
        user_id=user.id,
        role_scope="platform",
        role_id=platform_role.id,
    )
    fk_db_session.add(pa)
    await fk_db_session.flush()

    res = await fk_db_session.execute(
        select(PlatformRoleAssignment).where(PlatformRoleAssignment.id == pa.id)
    )
    assignment = res.scalar_one()
    assert assignment.user_id == user.id
    assert assignment.role_id == platform_role.id
    assert assignment.role_scope == "platform"


@pytest.mark.asyncio
async def test_org_role_permission_requires_organization_id(
    fk_db_session: AsyncSession,
):
    """9. Organization RolePermission requires non-null organization_id."""
    org = Organization(id=uuid.uuid4(), name="Org Meerut", slug="org-meerut-rp")
    role = Role(
        id=uuid.uuid4(),
        name="Org Role",
        scope="organization",
        organization_id=org.id,
    )
    perm = Permission(id=uuid.uuid4(), code="campaign:view")
    fk_db_session.add_all([org, role, perm])
    await fk_db_session.flush()

    invalid_rp = RolePermission(
        role_id=role.id,
        permission_id=perm.id,
        role_scope="organization",
        organization_id=None,
    )
    fk_db_session.add(invalid_rp)
    with pytest.raises(IntegrityError):
        await fk_db_session.flush()


@pytest.mark.asyncio
async def test_platform_role_permission_requires_null_organization_id(
    fk_db_session: AsyncSession,
):
    """10. Platform RolePermission requires null organization_id."""
    org = Organization(id=uuid.uuid4(), name="Org Meerut 2", slug="org-meerut-rp2")
    plat_role = Role(
        id=uuid.uuid4(),
        name="Plat Role",
        scope="platform",
        organization_id=None,
    )
    perm = Permission(id=uuid.uuid4(), code="system:inspect")
    fk_db_session.add_all([org, plat_role, perm])
    await fk_db_session.flush()

    invalid_rp = RolePermission(
        role_id=plat_role.id,
        permission_id=perm.id,
        role_scope="platform",
        organization_id=org.id,
    )
    fk_db_session.add(invalid_rp)
    with pytest.raises(IntegrityError):
        await fk_db_session.flush()


@pytest.mark.asyncio
async def test_role_permission_cannot_reference_role_with_wrong_organization(
    fk_db_session: AsyncSession,
):
    """11. A RolePermission cannot reference a role with the wrong organization."""
    org_a = Organization(id=uuid.uuid4(), name="Org Alpha", slug="org-alpha-rp")
    org_b = Organization(id=uuid.uuid4(), name="Org Beta", slug="org-beta-rp")
    role_a = Role(
        id=uuid.uuid4(),
        name="Role A",
        scope="organization",
        organization_id=org_a.id,
    )
    perm = Permission(id=uuid.uuid4(), code="reports:export")
    fk_db_session.add_all([org_a, org_b, role_a, perm])
    await fk_db_session.flush()

    # Mismatch: role belongs to org_a, but association claims org_b
    invalid_rp = RolePermission(
        role_id=role_a.id,
        permission_id=perm.id,
        role_scope="organization",
        organization_id=org_b.id,
    )
    fk_db_session.add(invalid_rp)
    with pytest.raises(IntegrityError):
        await fk_db_session.flush()


@pytest.mark.asyncio
async def test_role_permission_cannot_reference_role_with_wrong_scope(
    fk_db_session: AsyncSession,
):
    """12. A RolePermission cannot reference a role with the wrong scope."""
    org = Organization(id=uuid.uuid4(), name="Org Scope", slug="org-scope-rp")
    org_role = Role(
        id=uuid.uuid4(),
        name="Org Scope Role",
        scope="organization",
        organization_id=org.id,
    )
    perm = Permission(id=uuid.uuid4(), code="audit:export")
    fk_db_session.add_all([org, org_role, perm])
    await fk_db_session.flush()

    # Mismatch: role has scope organization, but association claims platform
    invalid_rp = RolePermission(
        role_id=org_role.id,
        permission_id=perm.id,
        role_scope="platform",
        organization_id=None,
    )
    fk_db_session.add(invalid_rp)
    with pytest.raises(IntegrityError):
        await fk_db_session.flush()


@pytest.mark.asyncio
async def test_role_permission_associations_load_through_sqlalchemy_relationships(
    fk_db_session: AsyncSession,
):
    """13. Role-permission associations load through SQLAlchemy relationships."""
    org = Organization(id=uuid.uuid4(), name="Org Rel", slug="org-rel-rp")
    role = Role(
        id=uuid.uuid4(),
        name="Rel Role",
        scope="organization",
        organization_id=org.id,
    )
    perm = Permission(id=uuid.uuid4(), code="messages:send")
    fk_db_session.add_all([org, role, perm])
    await fk_db_session.flush()

    rp = RolePermission(
        role_id=role.id,
        permission_id=perm.id,
        role_scope="organization",
        organization_id=org.id,
    )
    fk_db_session.add(rp)
    await fk_db_session.flush()

    # Load from Role side
    stmt_role = (
        select(Role)
        .where(Role.id == role.id)
        .options(selectinload(Role.permissions))
    )
    loaded_role = (await fk_db_session.execute(stmt_role)).scalar_one()
    assert len(loaded_role.permissions) == 1
    assert loaded_role.permissions[0].code == "messages:send"

    # Load from Permission side
    stmt_perm = (
        select(Permission)
        .where(Permission.id == perm.id)
        .options(selectinload(Permission.roles))
    )
    loaded_perm = (await fk_db_session.execute(stmt_perm)).scalar_one()
    assert len(loaded_perm.roles) == 1
    assert loaded_perm.roles[0].name == "Rel Role"


@pytest.mark.asyncio
async def test_org_role_seeding_creates_correctly_scoped_associations(
    fk_db_session: AsyncSession,
):
    """14. Organization role seeding creates correctly scoped associations."""
    org = Organization(id=uuid.uuid4(), name="Org Seed", slug="org-seed-rp")
    fk_db_session.add(org)
    await fk_db_session.flush()

    repo = RoleRepository(fk_db_session)
    seeded_roles = await repo.seed_organization_roles(org.id)

    role_ids = [r.id for r in seeded_roles.values()]
    stmt = select(RolePermission).where(RolePermission.role_id.in_(role_ids))
    rps = (await fk_db_session.execute(stmt)).scalars().all()

    assert len(rps) > 0
    for rp in rps:
        assert rp.role_scope == "organization"
        assert rp.organization_id == org.id
        assert rp.role_id in role_ids


@pytest.mark.asyncio
async def test_rerunning_seeding_does_not_duplicate_associations(
    fk_db_session: AsyncSession,
):
    """15. Re-running role seeding does not duplicate associations."""
    org = Organization(id=uuid.uuid4(), name="Org ReSeed", slug="org-reseed-rp")
    fk_db_session.add(org)
    await fk_db_session.flush()

    repo = RoleRepository(fk_db_session)
    await repo.seed_organization_roles(org.id)
    initial_rps = (
        (await fk_db_session.execute(select(RolePermission))).scalars().all()
    )

    # Re-run seeding for the same organization
    await repo.seed_organization_roles(org.id)
    subsequent_rps = (
        (await fk_db_session.execute(select(RolePermission))).scalars().all()
    )

    assert len(initial_rps) == len(subsequent_rps)


@pytest.mark.asyncio
async def test_permission_lookup_never_uses_stale_session_tenant_context(
    fk_db_session: AsyncSession,
):
    """A caller must provide a verified org ID after rollback/transaction reuse."""
    org = Organization(id=uuid.uuid4(), name="Context Org", slug="context-org")
    fk_db_session.add(org)
    await fk_db_session.flush()

    repo = RoleRepository(fk_db_session)
    roles = await repo.seed_organization_roles(org.id)
    admin_role = roles["Organization Administrator"]

    # Simulate stale Python session metadata left by a completed transaction.
    fk_db_session.info["current_org"] = org.id
    assert await repo.get_permissions_for_roles([admin_role.id]) == []

    permissions = await repo.get_permissions_for_roles(
        [admin_role.id], organization_id=org.id
    )
    assert "members:read" in permissions

