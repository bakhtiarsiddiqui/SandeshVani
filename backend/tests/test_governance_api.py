import pytest
from httpx import AsyncClient

PASSWORD = "GovernancePassword123!"


async def _register_and_verify(
    client: AsyncClient,
    email: str,
    development_mail_sink,
) -> None:
    registration = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": "Governance Test User",
        },
    )
    assert registration.status_code == 201, registration.text
    message = development_mail_sink.consume_latest(email, "email-verification")
    assert message is not None and message.token
    verification = await client.post(
        "/api/v1/auth/verify-email", json={"token": message.token}
    )
    assert verification.status_code == 200, verification.text


async def _login(client: AsyncClient, email: str) -> dict:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_governance_workflow_requires_evidence_and_independent_approval(
    async_client: AsyncClient,
    development_mail_sink,
):
    await _register_and_verify(
        async_client, "governance-owner@example.com", development_mail_sink
    )
    owner = await _login(async_client, "governance-owner@example.com")
    org_response = await async_client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
        json={"name": "Governance Test Org", "slug": "governance-test-org"},
    )
    assert org_response.status_code == 201, org_response.text
    organization_id = org_response.json()["id"]
    owner_headers = {
        "Authorization": f"Bearer {owner['access_token']}",
        "X-Organization-ID": organization_id,
        "X-CSRF-Token": owner["csrf_token"],
    }

    audience = await async_client.post(
        "/api/v1/audiences",
        headers=owner_headers,
        json={
            "full_name": "Asha Governance",
            "email": "asha.governance@example.com",
            "preferred_language": "hi",
            "state_code": "UP",
            "city": "Meerut",
        },
    )
    assert audience.status_code == 201, audience.text
    audience_id = audience.json()["id"]

    basis = await async_client.post(
        "/api/v1/governance/consent/processing-basis",
        headers=owner_headers,
        json={
            "audience_member_id": audience_id,
            "purpose_code": "dengue_prevention",
            "event_type": "established",
            "basis_code": "consent",
            "evidence_source": "signed_form",
            "evidence_reference": "FORM-2026-0001",
        },
    )
    assert basis.status_code == 201, basis.text

    consent = await async_client.post(
        "/api/v1/governance/consent/channel-events",
        headers=owner_headers,
        json={
            "audience_member_id": audience_id,
            "channel": "email",
            "purpose_code": "dengue_prevention",
            "decision": "granted",
            "evidence_source": "signed_form",
            "evidence_reference": "FORM-2026-0001",
        },
    )
    assert consent.status_code == 201, consent.text

    suppressed = await async_client.post(
        "/api/v1/governance/consent/suppressions",
        headers=owner_headers,
        json={
            "audience_member_id": audience_id,
            "channel": "email",
            "event_type": "suppressed",
            "reason_code": "user_opt_out",
            "source_code": "preference_center",
        },
    )
    assert suppressed.status_code == 201, suppressed.text
    unsuppressed = await async_client.post(
        "/api/v1/governance/consent/suppressions",
        headers=owner_headers,
        json={
            "audience_member_id": audience_id,
            "channel": "email",
            "event_type": "unsuppressed",
            "reason_code": "verified_reconsent",
            "source_code": "preference_center",
        },
    )
    assert unsuppressed.status_code == 201, unsuppressed.text

    segment = await async_client.post(
        "/api/v1/governance/segments",
        headers=owner_headers,
        json={"name": "Meerut Hindi Residents"},
    )
    assert segment.status_code == 201, segment.text
    segment_id = segment.json()["id"]
    segment_version = await async_client.post(
        f"/api/v1/governance/segments/{segment_id}/versions",
        headers=owner_headers,
        json={
            "filter_ast": {
                "op": "and",
                "children": [
                    {"field": "state_code", "operator": "eq", "value": "IN-UP"},
                    {"field": "city", "operator": "eq", "value": "Meerut"},
                    {"field": "preferred_language", "operator": "eq", "value": "hi"},
                ],
            }
        },
    )
    assert segment_version.status_code == 201, segment_version.text
    version_id = segment_version.json()["id"]
    preview = await async_client.post(
        f"/api/v1/governance/segments/{segment_id}/preview",
        headers={
            "Authorization": f"Bearer {owner['access_token']}",
            "X-Organization-ID": organization_id,
        },
        json={"version_id": version_id},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["matched_count"] == 1

    template = await async_client.post(
        "/api/v1/governance/templates",
        headers=owner_headers,
        json={"name": "Dengue Prevention Notice"},
    )
    assert template.status_code == 201, template.text
    template_version = await async_client.post(
        f"/api/v1/governance/templates/{template.json()['id']}/versions",
        headers=owner_headers,
        json={
            "variants": {
                "email": {
                    "en": {
                        "subject": "Dengue prevention",
                        "body": "Remove standing water.",
                    },
                    "hi": {"subject": "डेंगू से बचाव", "body": "जमा पानी हटाएँ।"},
                }
            }
        },
    )
    assert template_version.status_code == 201, template_version.text

    campaign = await async_client.post(
        "/api/v1/governance/campaigns",
        headers=owner_headers,
        json={
            "name": "Meerut Dengue Prevention",
            "objective": "Share dengue prevention guidance",
            "purpose_code": "dengue_prevention",
        },
    )
    assert campaign.status_code == 201, campaign.text
    campaign_id = campaign.json()["id"]
    content_variants = {
        "email": {
            "en": {"subject": "Dengue prevention", "body": "Remove standing water."},
            "hi": {"subject": "डेंगू से बचाव", "body": "जमा पानी हटाएँ।"},
        }
    }
    campaign_version = await async_client.post(
        f"/api/v1/governance/campaigns/{campaign_id}/versions",
        headers=owner_headers,
        json={
            "channels": ["email"],
            "languages": ["en", "hi"],
            "segment_version_id": version_id,
            "template_version_id": template_version.json()["id"],
            "rendered_variants": content_variants,
        },
    )
    assert campaign_version.status_code == 201, campaign_version.text
    campaign_version_id = campaign_version.json()["id"]
    content_hash = campaign_version.json()["content_hash"]

    submitted = await async_client.post(
        f"/api/v1/governance/campaigns/{campaign_id}/versions/{campaign_version_id}/submit",
        headers=owner_headers,
    )
    assert submitted.status_code == 200, submitted.text

    # Give the campaign creator an Approver role too: the service must still
    # prohibit that user from approving their own submitted version.
    role_list = await async_client.get(
        f"/api/v1/organizations/{organization_id}/roles",
        headers={
            "Authorization": f"Bearer {owner['access_token']}",
            "X-Organization-ID": organization_id,
        },
    )
    assert role_list.status_code == 200, role_list.text
    approver_role = next(
        role for role in role_list.json() if role["name"] == "Approver"
    )
    member_list = await async_client.get(
        f"/api/v1/organizations/{organization_id}/members",
        headers={
            "Authorization": f"Bearer {owner['access_token']}",
            "X-Organization-ID": organization_id,
        },
    )
    assert member_list.status_code == 200, member_list.text
    owner_membership = next(
        row for row in member_list.json() if row["user_id"] == owner["user"]["id"]
    )
    assigned = await async_client.post(
        f"/api/v1/organizations/{organization_id}/members/{owner_membership['id']}/roles",
        headers=owner_headers,
        json={"role_id": approver_role["id"]},
    )
    assert assigned.status_code == 200, assigned.text
    self_approval = await async_client.post(
        f"/api/v1/governance/campaigns/{campaign_id}/versions/{campaign_version_id}/approval",
        headers=owner_headers,
        json={"decision": "approved", "rationale": "I created this version."},
    )
    assert self_approval.status_code == 403, self_approval.text

    await _register_and_verify(
        async_client, "independent-approver@example.com", development_mail_sink
    )
    added = await async_client.post(
        f"/api/v1/organizations/{organization_id}/members",
        headers=owner_headers,
        json={
            "email": "independent-approver@example.com",
            "role_ids": [approver_role["id"]],
        },
    )
    assert added.status_code == 201, added.text
    approver = await _login(async_client, "independent-approver@example.com")
    approver_headers = {
        "Authorization": f"Bearer {approver['access_token']}",
        "X-Organization-ID": organization_id,
        "X-CSRF-Token": approver["csrf_token"],
    }
    decision = await async_client.post(
        f"/api/v1/governance/campaigns/{campaign_id}/versions/{campaign_version_id}/approval",
        headers=approver_headers,
        json={
            "decision": "approved",
            "rationale": "Reviewed the exact submitted content.",
        },
    )
    assert decision.status_code == 201, decision.text
    assert decision.json()["version_hash"] == content_hash

    execution = await async_client.post(
        f"/api/v1/governance/campaigns/{campaign_id}/versions/{campaign_version_id}/execute",
        headers=owner_headers,
    )
    assert execution.status_code == 202, execution.text
    assert execution.json()["execution_mode"] == "mock"
    assert execution.json()["status"] == "queued"

    analytics = await async_client.get(
        f"/api/v1/governance/executions/{execution.json()['id']}/analytics",
        headers={
            "Authorization": f"Bearer {owner['access_token']}",
            "X-Organization-ID": organization_id,
        },
    )
    assert analytics.status_code == 200, analytics.text
    assert analytics.json()["simulated"] is True
    assert analytics.json()["delivered"] == 0
    assert analytics.json()["accepted"] == 0

    audit = await async_client.get(
        "/api/v1/governance/audit",
        headers={
            "Authorization": f"Bearer {owner['access_token']}",
            "X-Organization-ID": organization_id,
        },
    )
    assert audit.status_code == 200, audit.text
    actions = {row["action"] for row in audit.json()["data"]}
    assert "campaign.version_approved" in actions
    assert "campaign.mock_execution_queued" in actions
