import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

import app.api.deps as auth_deps
from app.models.auth_session import AuthSession
from app.models.user import User


@pytest.mark.asyncio
async def test_expired_database_session_rejects_unexpired_access_claims(
    test_db_session, monkeypatch
):
    user = User(
        email="expired-session@example.test",
        normalized_email="expired-session@example.test",
        password_hash="unused",
        full_name="Expired Session",
        status="active",
    )
    test_db_session.add(user)
    await test_db_session.flush()

    session_id = uuid.uuid4()
    test_db_session.add(
        AuthSession(
            id=session_id,
            user_id=user.id,
            created_at=datetime.now(UTC) - timedelta(days=8),
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
    )
    await test_db_session.commit()

    monkeypatch.setattr(
        auth_deps,
        "verify_access_token",
        lambda _token: {
            "sub": str(user.id),
            "session_id": str(session_id),
        },
    )
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="validly-signed-but-session-expired"
    )
    with pytest.raises(HTTPException) as error:
        await auth_deps.get_current_user(credentials, test_db_session)

    assert error.value.status_code == 401
