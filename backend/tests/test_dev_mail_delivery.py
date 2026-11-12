import pytest

from app.core.config import Settings
from app.core.dev_mail_delivery import deliver_local_auth_email


class FakeSMTP:
    sent_messages = []

    def __init__(self, host, port, timeout):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.logged_in = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def starttls(self):
        self.started_tls = True

    def login(self, username, password):
        self.logged_in = True

    def send_message(self, message):
        self.sent_messages.append(message)


@pytest.mark.asyncio
async def test_local_auth_email_is_sent_to_configured_smtp(monkeypatch):
    FakeSMTP.sent_messages.clear()
    monkeypatch.setattr("app.core.dev_mail_delivery.smtplib.SMTP", FakeSMTP)

    settings = Settings(
        _env_file=None,
        app_env="local",
        deployment_environment="development",
        enable_local_mail_sink=True,
        dev_mail_smtp_host="127.0.0.1",
        dev_mail_smtp_port=1025,
        dev_mail_from="no-reply@sandeshvani.local",
    )

    await deliver_local_auth_email(
        settings=settings,
        recipient="developer@example.com",
        purpose="email-verification",
        token="opaque-verification-token",
        lifetime_seconds=86400,
    )

    assert len(FakeSMTP.sent_messages) == 1
    message = FakeSMTP.sent_messages[0]
    assert message["To"] == "developer@example.com"
    assert message["From"] == "no-reply@sandeshvani.local"
    assert "Verify your SandeshVani email address" in message["Subject"]
    assert "opaque-verification-token" in message.get_content()


@pytest.mark.asyncio
async def test_local_auth_email_does_not_send_without_local_opt_in(monkeypatch):
    FakeSMTP.sent_messages.clear()
    monkeypatch.setattr("app.core.dev_mail_delivery.smtplib.SMTP", FakeSMTP)

    settings = Settings(
        _env_file=None,
        app_env="local",
        deployment_environment="development",
        enable_local_mail_sink=False,
        dev_mail_smtp_host="127.0.0.1",
    )

    with pytest.raises(RuntimeError, match="local development mail sink"):
        await deliver_local_auth_email(
            settings=settings,
            recipient="developer@example.com",
            purpose="email-verification",
            token="opaque-token",
            lifetime_seconds=86400,
        )

    assert FakeSMTP.sent_messages == []
