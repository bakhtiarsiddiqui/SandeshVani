import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.security import generate_secure_token, hash_token, verify_access_token
from app.models.auth_session import AuthSession
from app.models.membership import Membership
from app.models.organization import Organization
from app.models.token import RefreshToken
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.organization_service import OrganizationService


@pytest.mark.asyncio
async def test_selected_organization_is_restored_after_refresh(test_db_session):
    now = datetime.now(UTC)
    user = User(
        email="org-restore@example.test",
        normalized_email="org-restore@example.test",
        password_hash="unused",
        full_name="Organization Restore",
        status="active",
    )
    organization_a = Organization(name="Restore A", slug="restore-a")
    organization_b = Organization(name="Restore B", slug="restore-b")
    test_db_session.add_all([user, organization_a, organization_b])
    await test_db_session.flush()
    test_db_session.add_all(
        [
            Membership(
                organization_id=organization_a.id,
                user_id=user.id,
                status="active",
            ),
            Membership(
                organization_id=organization_b.id,
                user_id=user.id,
                status="active",
            ),
        ]
    )
    session_id = uuid.uuid4()
    auth_session = AuthSession(
        id=session_id,
        user_id=user.id,
        created_at=now,
        expires_at=now + timedelta(days=7),
    )
    raw_refresh = generate_secure_token(48)
    test_db_session.add(auth_session)
    test_db_session.add(
        RefreshToken(
            session_id=session_id,
            token_hash=hash_token(raw_refresh),
            family_id=uuid.uuid4(),
            created_at=now,
            expires_at=now + timedelta(days=7),
        )
    )
    await test_db_session.flush()

    await OrganizationService(test_db_session).switch_organization_context(
        user_id=user.id,
        session_id=session_id,
        target_organization_id=organization_b.id,
    )
    await test_db_session.commit()
    assert auth_session.selected_organization_id == organization_b.id

    rotated = await AuthService(test_db_session).rotate_refresh_token(raw_refresh)
    claims = verify_access_token(rotated["access_token"])
    assert claims["org_id"] == str(organization_b.id)
