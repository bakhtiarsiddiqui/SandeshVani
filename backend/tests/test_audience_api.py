import uuid

from httpx import AsyncClient
from pytest import mark


PASSWORD = "CommonPassword123!"


async def _register_login(
    client: AsyncClient,
    email: str,
    development_mail_sink,
) -> tuple[str, str]:
    registration = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": "Audience Test User",
        },
    )
    assert registration.status_code == 201
    message = development_mail_sink.consume_latest(email, "email-verification")
    assert message is not None and message.token is not None
    verification = await client.post(
        "/api/v1/auth/verify-email",
        json={"token": message.token},
    )
    assert verification.status_code == 200
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login.status_code == 200
    result = login.json()
    return result["access_token"], result["csrf_token"]


async def _create_org(client: AsyncClient, token: str, slug: str) -> dict:
    response = await client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": f"Audience {slug}", "slug": slug},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _tenant_headers(
    token: str, org_id: str | uuid.UUID, csrf: str | None = None
) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Organization-ID": org_id,
    }
    if csrf:
        headers["X-CSRF-Token"] = csrf
    return headers


@mark.asyncio
async def test_audience_crud_and_filters(
    async_client: AsyncClient,
    development_mail_sink,
):
    token, csrf = await _register_login(
        async_client, "audience-admin@example.org", development_mail_sink
    )
    org = await _create_org(async_client, token, "audience-crud-org")
    headers = _tenant_headers(token, org["id"], csrf)

    created = await async_client.post(
        "/api/v1/audiences",
        headers=headers,
        json={
            "full_name": "  Asha Sharma  ",
            "email": "ASHA@EXAMPLE.ORG",
            "phone": "+919876543210",
            "preferred_language": "hi",
            "district": "Meerut",
        },
    )
    assert created.status_code == 201, created.text
    member = created.json()
    assert member["full_name"] == "Asha Sharma"
    assert member["email"] == "asha@example.org"
    assert member["phone"] == "+919876543210"
    assert member["preferred_language"] == "hi"
    assert member["organization_id"] == org["id"]
    assert "created_by" not in member

    listed = await async_client.get(
        "/api/v1/audiences",
        headers=headers,
        params={"status": "active", "district": "meerut", "language": "hi"},
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["data"][0]["id"] == member["id"]
    assert listed.json()["pagination"] == {
        "next_cursor": None,
        "has_more": False,
        "limit": 25,
    }

    searched = await async_client.get(
        "/api/v1/audiences",
        headers=headers,
        params={"search": "asha"},
    )
    assert [row["id"] for row in searched.json()["data"]] == [member["id"]]

    fetched = await async_client.get(
        f"/api/v1/audiences/{member['id']}",
        headers=headers,
    )
    assert fetched.status_code == 200
    assert fetched.json()["id"] == member["id"]

    updated = await async_client.patch(
        f"/api/v1/audiences/{member['id']}",
        headers=headers,
        json={
            "full_name": "Asha Sharma Singh",
            "phone": None,
            "district": "Ghaziabad",
            "status": "inactive",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["full_name"] == "Asha Sharma Singh"
    assert updated.json()["phone"] is None
    assert updated.json()["email"] == "asha@example.org"
    assert updated.json()["district"] == "Ghaziabad"
    assert updated.json()["status"] == "inactive"


@mark.asyncio
async def test_audience_contact_validation_and_patch_cannot_remove_last_contact(
    async_client: AsyncClient,
    development_mail_sink,
):
    token, csrf = await _register_login(
        async_client, "audience-validation@example.org", development_mail_sink
    )
    org = await _create_org(async_client, token, "audience-validation-org")
    headers = _tenant_headers(token, org["id"], csrf)

    no_contact = await async_client.post(
        "/api/v1/audiences",
        headers=headers,
        json={"full_name": "No Contact"},
    )
    assert no_contact.status_code == 422

    invalid_phone = await async_client.post(
        "/api/v1/audiences",
        headers=headers,
        json={"full_name": "Bad Phone", "phone": "9876543210"},
    )
    assert invalid_phone.status_code == 422

    created = await async_client.post(
        "/api/v1/audiences",
        headers=headers,
        json={"full_name": "Phone Only", "phone": "+919876543210"},
    )
    assert created.status_code == 201, created.text

    removed_last_contact = await async_client.patch(
        f"/api/v1/audiences/{created.json()['id']}",
        headers=headers,
        json={"phone": None},
    )
    assert removed_last_contact.status_code == 422

    unchanged = await async_client.get(
        f"/api/v1/audiences/{created.json()['id']}",
        headers=headers,
    )
    assert unchanged.json()["phone"] == "+919876543210"


@mark.asyncio
async def test_audience_cursor_pagination_is_stable(
    async_client: AsyncClient,
    development_mail_sink,
):
    token, csrf = await _register_login(
        async_client, "audience-pages@example.org", development_mail_sink
    )
    org = await _create_org(async_client, token, "audience-pages-org")
    headers = _tenant_headers(token, org["id"], csrf)

    created_ids = []
    for name in ("Page One", "Page Two", "Page Three"):
        response = await async_client.post(
            "/api/v1/audiences",
            headers=headers,
            json={
                "full_name": name,
                "email": f"{name.lower().replace(' ', '.')}@example.org",
            },
        )
        assert response.status_code == 201, response.text
        created_ids.append(response.json()["id"])

    first = await async_client.get(
        "/api/v1/audiences", headers=headers, params={"limit": 1}
    )
    assert first.status_code == 200
    first_data = first.json()
    assert len(first_data["data"]) == 1
    assert first_data["pagination"]["has_more"] is True

    seen = [first_data["data"][0]["id"]]
    cursor = first_data["pagination"]["next_cursor"]
    while cursor:
        page = await async_client.get(
            "/api/v1/audiences",
            headers=headers,
            params={"limit": 1, "cursor": cursor},
        )
        assert page.status_code == 200, page.text
        payload = page.json()
        seen.extend(row["id"] for row in payload["data"])
        cursor = payload["pagination"]["next_cursor"]

    assert set(seen) == set(created_ids)
    assert len(seen) == len(set(seen)) == 3


@mark.asyncio
async def test_audience_access_is_tenant_scoped(
    async_client: AsyncClient,
    development_mail_sink,
):
    token_a, csrf_a = await _register_login(
        async_client, "audience-a@example.org", development_mail_sink
    )
    token_b, _ = await _register_login(
        async_client, "audience-b@example.org", development_mail_sink
    )
    org_a = await _create_org(async_client, token_a, "audience-tenant-a")
    org_b = await _create_org(async_client, token_b, "audience-tenant-b")

    created = await async_client.post(
        "/api/v1/audiences",
        headers=_tenant_headers(token_a, org_a["id"], csrf_a),
        json={"full_name": "Tenant A Person", "email": "person@tenant-a.example"},
    )
    assert created.status_code == 201, created.text

    denied_list = await async_client.get(
        "/api/v1/audiences",
        headers=_tenant_headers(token_b, org_a["id"]),
    )
    assert denied_list.status_code == 403

    denied_record = await async_client.get(
        f"/api/v1/audiences/{created.json()['id']}",
        headers=_tenant_headers(token_b, org_a["id"]),
    )
    assert denied_record.status_code == 403

    own_list = await async_client.get(
        "/api/v1/audiences",
        headers=_tenant_headers(token_b, org_b["id"]),
    )
    assert own_list.status_code == 200
    assert own_list.json()["data"] == []


@mark.asyncio
async def test_audience_permissions_are_enforced(
    async_client: AsyncClient,
    development_mail_sink,
):
    admin_token, admin_csrf = await _register_login(
        async_client,
        "audience-permissions-admin@example.org",
        development_mail_sink,
    )
    org = await _create_org(async_client, admin_token, "audience-permissions-org")
    org_id = org["id"]
    headers = _tenant_headers(admin_token, org_id, admin_csrf)

    roles_response = await async_client.get(
        f"/api/v1/organizations/{org_id}/roles",
        headers=headers,
    )
    assert roles_response.status_code == 200
    role_id = next(
        role["id"]
        for role in roles_response.json()
        if role["name"] == "Communication Team"
    )

    member_email = "audience-read-only@example.org"
    member_token, member_csrf = await _register_login(
        async_client, member_email, development_mail_sink
    )
    add_response = await async_client.post(
        f"/api/v1/organizations/{org_id}/members",
        headers=headers,
        json={"email": member_email, "role_ids": [role_id]},
    )
    assert add_response.status_code == 201, add_response.text

    member_headers = _tenant_headers(member_token, org_id, member_csrf)
    readable = await async_client.get("/api/v1/audiences", headers=member_headers)
    assert readable.status_code == 200

    forbidden = await async_client.post(
        "/api/v1/audiences",
        headers=member_headers,
        json={"full_name": "No Permission", "email": "no-permission@example.org"},
    )
    assert forbidden.status_code == 403
