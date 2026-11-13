import pytest

from app.core.config import Settings
from app.core.resend_email import _email_content, deliver_resend_auth_email


def _settings(**overrides):
    values = {
        "_env_file": None,
        "app_env": "local",
        "deployment_environment": "development",
        "resend_api_key": "re_test_key",
        "auth_email_from": "SandeshVani <onboarding@resend.dev>",
        "frontend_base_url": "https://sandeshvani.vercel.app",
    }
    values.update(overrides)
    return Settings(**values)


def test_verification_email_uses_existing_frontend_token_route():
    subject, text, html = _email_content(
        _settings(), "email-verification", "token+/value", 86400
    )
    assert subject == "Verify your SandeshVani email address"
    assert "https://sandeshvani.vercel.app/?verify_token=token%2B%2Fvalue" in text
    assert "verify_token=token%2B%2Fvalue" in html
    assert "24 minutes" not in text
    assert "1440 minutes" in text


def test_password_reset_email_uses_reset_token_route():
    _, text, _ = _email_content(_settings(), "password-reset", "opaque-token", 3600)
    assert "https://sandeshvani.vercel.app/?reset_token=opaque-token" in text
    assert "60 minutes" in text


def test_unknown_account_email_has_no_actionable_token_link():
    _, text, html = _email_content(_settings(), "password-reset", None, 3600)
    assert "reset_token" not in text
    assert "reset_token" not in html
    assert "ignore this email" in text


@pytest.mark.asyncio
async def test_resend_posts_to_server_side_api(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            captured["timeout"] = kwargs["timeout"]

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, *, json, headers):
            captured.update({"url": url, "json": json, "headers": headers})
            return FakeResponse()

    monkeypatch.setattr("app.core.resend_email.httpx.AsyncClient", FakeAsyncClient)
    settings = _settings()
    await deliver_resend_auth_email(
        settings, "recipient@example.com", "email-verification", "secret-token", 86400
    )

    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["json"]["to"] == ["recipient@example.com"]
    assert captured["json"]["from"] == settings.auth_email_from
    assert "secret-token" in captured["json"]["text"]
    assert captured["headers"]["Authorization"] == "Bearer re_test_key"
