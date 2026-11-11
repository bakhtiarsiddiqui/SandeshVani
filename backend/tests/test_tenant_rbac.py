import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.membership import Membership


async def _register_and_login(
    client: AsyncClient, email: str, development_mail_sink
) -> tuple[str, str]:
    password = "CommonPassword123!"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert reg.status_code == 201
    mail = development_mail_sink.consume_latest(email, "email-verification")
    assert mail is not None and mail.token is not None
    token = mail.token
    await client.post("/api/v1/auth/verify-email", json={"token": token})

    login_res = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    data = login_res.json()
    return data["access_token"], data["csrf_token"]


@pytest.mark.asyncio
async def test_organization_provisioning_and_admin_role(
    async_client: AsyncClient, development_mail_sink
):
    token, _ = await _register_and_login(
        async_client, "creator@nagarnigam.gov.in", development_mail_sink
    )

    # Create new organization
    org_res = await async_client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Nagar Nigam Meerut", "slug": "nn-meerut"},
    )
    assert org_res.status_code == 201
    org_data = org_res.json()
    assert org_data["slug"] == "nn-meerut"

    # Verify /auth/me returns active organization and admin permissions
    me_res = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["active_organization"]["slug"] == "nn-meerut"
    assert "members:read" in me_data["permissions"]
    assert "campaigns:create" in me_data["permissions"]


@pytest.mark.asyncio
async def test_multiple_organizations_and_switching(
    async_client: AsyncClient, development_mail_sink
):
    token, _ = await _register_and_login(
        async_client, "director@state.gov.in", development_mail_sink
    )

    # Create Org 1
    await async_client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Health Department", "slug": "health-dept"},
    )

    # Create Org 2
    org2_res = await async_client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Education Department", "slug": "edu-dept"},
    )
    org2_id = org2_res.json()["id"]

    # List user organizations
    list_res = await async_client.get(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_res.status_code == 200
    slugs = [o["slug"] for o in list_res.json()]
    assert "health-dept" in slugs
    assert "edu-dept" in slugs

    # Switch to Org 2
    switch_res = await async_client.post(
        "/api/v1/auth/select-org",
        headers={"Authorization": f"Bearer {token}"},
        json={"organization_id": org2_id},
    )
    assert switch_res.status_code == 200
    new_token = switch_res.json()["access_token"]
    assert switch_res.json()["active_organization"]["slug"] == "edu-dept"

    # Use new token to query current organization
    curr_res = await async_client.get(
        "/api/v1/organizations/current",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert curr_res.status_code == 200
    assert curr_res.json()["id"] == org2_id


@pytest.mark.asyncio
async def test_cross_tenant_access_denial(
    async_client: AsyncClient, development_mail_sink
):
    token_a, _ = await _register_and_login(
        async_client, "admin_a@tenant-a.gov.in", development_mail_sink
    )
    token_b, _ = await _register_and_login(
        async_client, "admin_b@tenant-b.gov.in", development_mail_sink
    )

    # Admin A creates Org A
    org_a = (
        await async_client.post(
            "/api/v1/organizations",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"name": "Tenant A Org", "slug": "tenant-a"},
        )
    ).json()

    # Admin B creates Org B
    await async_client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"name": "Tenant B Org", "slug": "tenant-b"},
    )

    # Admin B tries to list members of Org A -> 403 Forbidden!
    forbidden_res = await async_client.get(
        f"/api/v1/organizations/{org_a['id']}/members",
        headers={
            "Authorization": f"Bearer {token_b}",
            "X-Organization-ID": org_a["id"],
        },
    )
    assert forbidden_res.status_code == 403
    assert "not an active member" in forbidden_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_organization_discovery_is_membership_scoped(
    async_client: AsyncClient, development_mail_sink
):
    """A user can neither list nor fetch another user's organization."""
    token_a, _ = await _register_and_login(
        async_client, "listing-a@tenant.gov.in", development_mail_sink
    )
    token_b, _ = await _register_and_login(
        async_client, "listing-b@tenant.gov.in", development_mail_sink
    )
    org_a = (
        await async_client.post(
            "/api/v1/organizations",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"name": "Listing A", "slug": "listing-a"},
        )
    ).json()
    org_b = (
        await async_client.post(
            "/api/v1/organizations",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"name": "Listing B", "slug": "listing-b"},
        )
    ).json()

    a_listing = await async_client.get(
        "/api/v1/organizations", headers={"Authorization": f"Bearer {token_a}"}
    )
    assert a_listing.status_code == 200
    assert [org["id"] for org in a_listing.json()] == [org_a["id"]]

    b_direct = await async_client.get(
        f"/api/v1/organizations/{org_a['id']}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert b_direct.status_code == 403
    assert org_b["id"] not in [org["id"] for org in a_listing.json()]


@pytest.mark.asyncio
async def test_revoked_membership_loses_tenant_access_on_next_request(
    async_client: AsyncClient,
    development_mail_sink,
    test_db_session,
):
    """Authorization must re-check membership rather than trust token org claims."""
    token, _ = await _register_and_login(
        async_client, "revoked-member@tenant.gov.in", development_mail_sink
    )
    org = (
        await async_client.post(
            "/api/v1/organizations",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Revocation Org", "slug": "revocation-org"},
        )
    ).json()

    membership = (
        await test_db_session.execute(
            select(Membership).where(Membership.organization_id == uuid.UUID(org["id"]))
        )
    ).scalar_one()
    membership.status = "revoked"
    await test_db_session.commit()

    response = await async_client.get(
        "/api/v1/organizations/current",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-ID": org["id"],
        },
    )
    assert response.status_code == 403
    assert "not an active member" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_multiple_roles_union_permissions(
    async_client: AsyncClient, development_mail_sink
):
    # Admin creates org
    admin_token, admin_csrf = await _register_and_login(
        async_client, "head@council.gov.in", development_mail_sink
    )
    org = (
        await async_client.post(
            "/api/v1/organizations",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Municipal Council", "slug": "municipal-council"},
        )
    ).json()
    org_id = org["id"]

    # Register member
    member_email = "officer@council.gov.in"
    await _register_and_login(async_client, member_email, development_mail_sink)

    # Fetch available roles
    roles_res = await async_client.get(
        f"/api/v1/organizations/{org_id}/roles",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Organization-ID": org_id,
        },
    )
    roles = {r["name"]: r["id"] for r in roles_res.json()}

    # Assign BOTH Campaign Manager AND Approver roles
    role_ids = [roles["Campaign Manager"], roles["Approver"]]

    add_res = await async_client.post(
        f"/api/v1/organizations/{org_id}/members",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Organization-ID": org_id,
            "X-CSRF-Token": admin_csrf,
        },
        json={"email": member_email, "role_ids": role_ids},
    )
    assert add_res.status_code == 201

    # Login as the member
    member_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": member_email, "password": "CommonPassword123!"},
    )
    member_data = member_login.json()

    # Verify UNION of permissions:
    # Campaign Manager has campaigns:submit, distribution:mock_execute
    # Approver has approvals:approve, approvals:reject
    perms = set(member_data["permissions"])
    assert "campaigns:submit" in perms
    assert "distribution:mock_execute" in perms
    assert "approvals:approve" in perms
    assert "approvals:reject" in perms
    # Neither role has members:create
    assert "members:create" not in perms
