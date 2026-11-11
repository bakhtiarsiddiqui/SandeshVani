import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_unauthorized_cross_origin_rejection(async_client: AsyncClient):
    # State-changing request with unauthorized origin
    res = await async_client.post(
        "/api/v1/auth/register",
        headers={"Origin": "https://malicious-phishing-site.com"},
        json={
            "email": "hacked@site.com",
            "password": "Password123!",
            "full_name": "Bad Actor",
        },
    )
    assert res.status_code == 403
    assert "cross-origin" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_csrf_token_required_for_member_mutation(
    async_client: AsyncClient,
    development_mail_sink,
):
    # Register & Login
    reg = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner@corp.gov.in",
            "password": "SecretPassword123!",
            "full_name": "Corp Owner",
        },
    )
    assert reg.status_code == 201
    mail = development_mail_sink.consume_latest(
        "owner@corp.gov.in", "email-verification"
    )
    assert mail is not None and mail.token is not None
    token = mail.token
    await async_client.post("/api/v1/auth/verify-email", json={"token": token})

    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "owner@corp.gov.in", "password": "SecretPassword123!"},
    )
    access_token = login_res.json()["access_token"]

    # Create Org
    org = (
        await async_client.post(
            "/api/v1/organizations",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"name": "Secure Org", "slug": "secure-org"},
        )
    ).json()

    # Attempt to add member without X-CSRF-Token -> 403
    no_csrf_res = await async_client.post(
        f"/api/v1/organizations/{org['id']}/members",
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-Organization-ID": org["id"],
        },
        json={"email": "test@corp.gov.in", "role_ids": []},
    )
    assert no_csrf_res.status_code == 403
    assert "csrf" in no_csrf_res.json()["detail"].lower()

