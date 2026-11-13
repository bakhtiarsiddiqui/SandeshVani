import pytest
from httpx import AsyncClient

from app.core.config import get_settings


@pytest.mark.asyncio
async def test_login_failures_are_persistently_throttled(
    async_client: AsyncClient,
):
    email = "throttle-target@example.com"
    settings = get_settings()

    for _ in range(settings.auth_login_email_limit):
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "DefinitelyWrong123!"},
        )
        assert response.status_code == 401

    blocked = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "DefinitelyWrong123!"},
    )
    assert blocked.status_code == 429
    assert blocked.headers["retry-after"] == str(
        settings.auth_login_rate_window_seconds
    )
