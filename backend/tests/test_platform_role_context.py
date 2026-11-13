import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Permission, PlatformRoleAssignment, Role, RolePermission
from app.models.user import User


@pytest.mark.asyncio
async def test_platform_context_returns_only_callers_global_assignments(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    development_mail_sink,
):
    email = "platform.operator@example.test"
    password = "StrongPassword99!"
    registration = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Platform Operator"},
    )
    assert registration.status_code == 201, registration.text
    mail = development_mail_sink.consume_latest(email, "email-verification")
    assert mail is not None and mail.token
    verification = await async_client.post(
        "/api/v1/auth/verify-email", json={"token": mail.token}
    )
    assert verification.status_code == 200, verification.text
    login = await async_client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    role = Role(
        id=uuid.uuid4(),
        name="Platform Operator",
        scope="platform",
        organization_id=None,
        description="Global operations",
        is_system_role=True,
    )
    permission = Permission(
        id=uuid.uuid4(),
        code="platform:organizations:read",
        description="Read platform organization directory",
    )
    other_user = User(
        id=uuid.uuid4(),
        email="other.operator@example.test",
        normalized_email="other.operator@example.test",
        password_hash="test-hash",
        full_name="Other Operator",
    )
    test_db_session.add_all([role, permission, other_user])
    await test_db_session.flush()
    test_db_session.add_all(
        [
            RolePermission(
                role_id=role.id,
                permission_id=permission.id,
                role_scope="platform",
                organization_id=None,
            ),
            PlatformRoleAssignment(
                user_id=uuid.UUID(registration.json()["user_id"]),
                role_scope="platform",
                role_id=role.id,
            ),
            PlatformRoleAssignment(
                user_id=other_user.id,
                role_scope="platform",
                role_id=role.id,
            ),
        ]
    )
    await test_db_session.commit()

    response = await async_client.get(
        "/api/v1/platform/me", headers={"Authorization": "Bearer " + token}
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert [role["name"] for role in payload["platform_roles"]] == ["Platform Operator"]
    assert payload["platform_permissions"] == ["platform:organizations:read"]
