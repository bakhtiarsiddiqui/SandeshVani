"""Tests for the AI router endpoints (/api/v1/ai/campaigns/...).

All tests run offline with FakeProvider and test API key.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from ai.config import AISettings, get_ai_settings
from ai.models import AIGenerationRequest  # noqa: F401
from ai.router import get_provider
from app.db.session import get_db
from app.main import app

TEST_API_KEY = "test-service-secret-key-12345"


@pytest.fixture
def mock_ai_settings():
    return AISettings(
        _env_file=None,
        ai_provider="ollama",
        ai_service_api_key=TEST_API_KEY,
    )


@pytest.fixture
async def ai_client(test_db_session, mock_ai_settings, fake_provider):
    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_ai_settings] = lambda: mock_ai_settings
    app.dependency_overrides[get_provider] = lambda: fake_provider

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_ai_settings, None)
    app.dependency_overrides.pop(get_provider, None)


SAMPLE_BRIEF_PAYLOAD = {
    "channel": "sms",
    "language": "hi",
    "tone": "professional",
    "key_facts": {
        "event": "Community Health Fair",
        "date": "2026-12-15",
        "venue": "Gandhi Maidan, Patna",
        "cost": "Free",
        "contact": "1800-XXX-YYYY",
    },
}


class TestAIGenerateEndpoint:
    async def test_missing_api_key_returns_401(self, ai_client):
        response = await ai_client.post(
            "/api/v1/ai/campaigns/generate",
            json=SAMPLE_BRIEF_PAYLOAD,
        )
        assert response.status_code == 401

    async def test_invalid_api_key_returns_403(self, ai_client):
        response = await ai_client.post(
            "/api/v1/ai/campaigns/generate",
            headers={"X-API-Key": "wrong-key"},
            json=SAMPLE_BRIEF_PAYLOAD,
        )
        assert response.status_code == 403

    async def test_valid_generate_returns_202_and_draft(self, ai_client):
        response = await ai_client.post(
            "/api/v1/ai/campaigns/generate",
            headers={"X-API-Key": TEST_API_KEY},
            json=SAMPLE_BRIEF_PAYLOAD,
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "pending_approval"
        assert len(data["drafts"]) == 1
        assert data["drafts"][0]["channel"] == "sms"
        assert data["drafts"][0]["language"] == "hi"
        assert "Gandhi Maidan, Patna" in data["drafts"][0]["text"]
        assert "request_id" in data

    async def test_invalid_language_returns_422(self, ai_client):
        payload = {**SAMPLE_BRIEF_PAYLOAD, "language": "unsupported"}
        response = await ai_client.post(
            "/api/v1/ai/campaigns/generate",
            headers={"X-API-Key": TEST_API_KEY},
            json=payload,
        )
        assert response.status_code == 422


class TestAIGetAndApproveEndpoints:
    async def test_get_generation_request(self, ai_client):
        # 1. Generate
        gen_res = await ai_client.post(
            "/api/v1/ai/campaigns/generate",
            headers={"X-API-Key": TEST_API_KEY},
            json=SAMPLE_BRIEF_PAYLOAD,
        )
        assert gen_res.status_code == 202
        req_id = gen_res.json()["request_id"]

        # 2. Get without key -> 401
        get_res_unauth = await ai_client.get(f"/api/v1/ai/campaigns/{req_id}")
        assert get_res_unauth.status_code == 401

        # 3. Get with key -> 200
        get_res = await ai_client.get(
            f"/api/v1/ai/campaigns/{req_id}",
            headers={"X-API-Key": TEST_API_KEY},
        )
        assert get_res.status_code == 200
        data = get_res.json()
        assert data["request_id"] == req_id
        assert data["status"] == "pending_approval"
        assert data["channel"] == "sms"
        assert data["draft"]["text"] is not None

    async def test_get_nonexistent_returns_404(self, ai_client):
        random_id = uuid.uuid4()
        res = await ai_client.get(
            f"/api/v1/ai/campaigns/{random_id}",
            headers={"X-API-Key": TEST_API_KEY},
        )
        assert res.status_code == 404

    async def test_approve_draft(self, ai_client):
        # 1. Generate
        gen_res = await ai_client.post(
            "/api/v1/ai/campaigns/generate",
            headers={"X-API-Key": TEST_API_KEY},
            json=SAMPLE_BRIEF_PAYLOAD,
        )
        req_id = gen_res.json()["request_id"]

        # 2. Approve
        approve_res = await ai_client.post(
            f"/api/v1/ai/campaigns/{req_id}/approve",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "action": "approve",
                "reviewer_note": "Looks great, approved for review.",
            },
        )
        assert approve_res.status_code == 200
        data = approve_res.json()
        assert data["status"] == "approved"
        assert data["action"] == "approve"

        # 3. Subsequent approval attempt is rejected (HTTP 400)
        re_approve_res = await ai_client.post(
            f"/api/v1/ai/campaigns/{req_id}/approve",
            headers={"X-API-Key": TEST_API_KEY},
            json={"action": "approve"},
        )
        assert re_approve_res.status_code == 400

    async def test_reject_draft(self, ai_client):
        # 1. Generate
        gen_res = await ai_client.post(
            "/api/v1/ai/campaigns/generate",
            headers={"X-API-Key": TEST_API_KEY},
            json=SAMPLE_BRIEF_PAYLOAD,
        )
        req_id = gen_res.json()["request_id"]

        # 2. Reject
        reject_res = await ai_client.post(
            f"/api/v1/ai/campaigns/{req_id}/approve",
            headers={"X-API-Key": TEST_API_KEY},
            json={"action": "reject", "reviewer_note": "Tone does not fit guidelines."},
        )
        assert reject_res.status_code == 200
        assert reject_res.json()["status"] == "rejected"
