import logging
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dev_mail import DevelopmentMailSink
from app.core.security import hash_token
from app.db.session import get_db
from app.main import create_app
from app.models.token import EmailVerificationToken, PasswordResetToken
from app.models.user import User


def _local_mail_token(sink, email: str, purpose: str) -> str:
    message = sink.consume_latest(email, purpose)
    assert message is not None
    assert message.token is not None
    return message.token


@pytest.mark.asyncio
async def test_registration_and_duplicate_rejection(async_client: AsyncClient):
    payload = {
        "email": "officer@department.gov.in",
        "password": "SecurePassword123!",
        "full_name": "Ramesh Kumar",
    }
    # 1. First registration
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "user_id" in data
    assert "dev_verification_token" not in data

    # 2. Duplicate registration
    dup_res = await async_client.post("/api/v1/auth/register", json=payload)
    assert dup_res.status_code == 409


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "app_env",
    [
        None,
        "",
        "production",
        "staging",
        "prodution",
        "locl",
        "local",
        "LOCAL",
        " local ",
    ],
    ids=[
        "missing",
        "empty",
        "production",
        "staging",
        "misspelled",
        "misspelled-local",
        "local-without-sink-opt-in",
        "uppercase",
        "padded",
    ],
)
async def test_dev_token_workflow_is_disabled_unless_environment_is_exact_local(
    test_db_session: AsyncSession,
    app_env: str | None,
    monkeypatch: pytest.MonkeyPatch,
):
    if app_env is None:
        monkeypatch.delenv("APP_ENV", raising=False)
    settings = Settings(
        _env_file=None, **({} if app_env is None else {"app_env": app_env})
    )
    test_app = create_app(settings)

    async def override_db():
        yield test_db_session

    test_app.dependency_overrides[get_db] = override_db
    test_app.dependency_overrides[get_settings] = lambda: settings

    from httpx import ASGITransport

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
        headers={"Origin": "http://localhost:5173"},
    ) as client:
        registration = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "gate-user@example.com",
                "password": "SecurePassword123!",
                "full_name": "New User",
            },
        )
        assert registration.status_code == 503
        assert "dev_verification_token" not in registration.text
        resend = await client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "gate-user@example.com"},
        )
        recovery = await client.post(
            "/api/v1/auth/password-recovery",
            json={"email": "gate-user@example.com"},
        )
        assert resend.status_code == recovery.status_code == 503
        assert "dev_token" not in resend.text
        assert "dev_token" not in recovery.text
        for path in (
            "/api/v1/auth/dev/verification-token",
            "/api/v1/auth/dev/password-reset-token",
        ):
            dev_route = await client.post(path, json={"email": "new-user@example.com"})
            assert dev_route.status_code == 404


@pytest.mark.asyncio
async def test_exact_local_environment_keeps_local_mail_flow_and_public_schema_clean(
    test_db_session: AsyncSession,
):
    settings = Settings(
        _env_file=None,
        app_env="local",
        deployment_environment="development",
        enable_local_mail_sink=True,
    )
    test_app = create_app(settings)

    async def override_db():
        yield test_db_session

    test_app.state.development_mail_sink.clear()
    test_app.dependency_overrides[get_db] = override_db
    test_app.dependency_overrides[get_settings] = lambda: settings
    schema = test_app.openapi()
    register_schema = schema["components"]["schemas"]["RegisterResponse"]
    assert "dev_verification_token" not in register_schema["properties"]
    assert not any(path.startswith("/api/v1/auth/dev/") for path in schema["paths"])

    from httpx import ASGITransport

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
        headers={"Origin": "http://localhost:5173"},
    ) as client:
        for path in (
            "/api/v1/auth/dev/verification-token",
            "/api/v1/auth/dev/password-reset-token",
        ):
            dev_route = await client.post(path, json={"email": "anyone@example.com"})
            assert dev_route.status_code == 404
        registration = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "local-user@example.com",
                "password": "SecurePassword123!",
                "full_name": "Local User",
            },
        )
        assert registration.status_code == 201
        assert "dev_verification_token" not in registration.json()
        token = _local_mail_token(
            test_app.state.development_mail_sink,
            "local-user@example.com",
            "email-verification",
        )
        verification = await client.post(
            "/api/v1/auth/verify-email", json={"token": token}
        )
        assert verification.status_code == 200

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as unauthenticated_client:
        for path in (
            "/api/v1/auth/dev/verification-token",
            "/api/v1/auth/dev/password-reset-token",
        ):
            response = await unauthenticated_client.post(
                path, json={"email": "local-user@example.com"}
            )
            assert response.status_code == 404


@pytest.mark.asyncio
async def test_production_openapi_excludes_development_token_contracts():
    settings = Settings(_env_file=None, app_env="production")
    test_app = create_app(settings)
    schema = test_app.openapi()
    register_response = schema["paths"]["/api/v1/auth/register"]["post"][
        "responses"
    ]["201"]
    register_ref = register_response["content"]["application/json"]["schema"]["$ref"]
    register_schema = schema["components"]["schemas"][register_ref.split("/")[-1]]
    assert "dev_verification_token" not in register_schema["properties"]
    for path in (
        "/api/v1/auth/resend-verification",
        "/api/v1/auth/password-recovery",
    ):
        response_schema = schema["paths"][path]["post"]["responses"]["200"]
        response_ref = response_schema["content"]["application/json"]["schema"]["$ref"]
        model = schema["components"]["schemas"][response_ref.split("/")[-1]]
        assert set(model["properties"]) == {"message"}
    assert "/api/v1/auth/dev/verification-token" not in schema["paths"]
    assert "/api/v1/auth/dev/password-reset-token" not in schema["paths"]
    assert "DevelopmentTokenResponse" not in schema["components"]["schemas"]


@pytest.mark.asyncio
async def test_local_openapi_contains_only_public_auth_contracts():
    settings = Settings(
        _env_file=None,
        app_env="local",
        deployment_environment="development",
        enable_local_mail_sink=True,
    )
    schema = create_app(settings).openapi()
    assert not any(path.startswith("/api/v1/auth/dev/") for path in schema["paths"])
    public_message_schema = schema["components"]["schemas"]["AuthMessageResponse"]
    assert set(public_message_schema["properties"]) == {"message"}
    assert "DevelopmentTokenResponse" not in schema["components"]["schemas"]


@pytest.mark.asyncio
async def test_public_resend_and_recovery_responses_do_not_enumerate_accounts(
    async_client: AsyncClient,
    development_mail_sink,
):
    known_email = "known-user@example.com"
    registration = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": known_email,
            "password": "SecurePassword123!",
            "full_name": "Known User",
        },
    )
    assert registration.status_code == 201

    for path in (
        "/api/v1/auth/resend-verification",
        "/api/v1/auth/password-recovery",
    ):
        known = await async_client.post(path, json={"email": known_email})
        unknown = await async_client.post(
            path, json={"email": "unknown-user@example.com"}
        )
        assert known.status_code == unknown.status_code == 200
        assert known.json() == unknown.json()
        assert "token" not in known.json()
    known_verification = development_mail_sink.consume_latest(
        known_email, "email-verification"
    )
    unknown_verification = development_mail_sink.consume_latest(
        "unknown-user@example.com", "email-verification"
    )
    known_reset = development_mail_sink.consume_latest(known_email, "password-reset")
    unknown_reset = development_mail_sink.consume_latest(
        "unknown-user@example.com", "password-reset"
    )
    assert known_verification is not None and known_verification.token is not None
    assert unknown_verification is not None and unknown_verification.token is None
    assert known_reset is not None and known_reset.token is not None
    assert unknown_reset is not None and unknown_reset.token is None


@pytest.mark.asyncio
async def test_known_and_unknown_accounts_receive_equivalent_email_rate_limits(
    test_db_session: AsyncSession,
):
    settings = Settings(
        _env_file=None,
        app_env="local",
        deployment_environment="development",
        enable_local_mail_sink=True,
        auth_recovery_email_limit=2,
        auth_recovery_ip_limit=100,
        auth_recovery_rate_window_seconds=600,
    )
    test_app = create_app(settings)

    async def override_db():
        yield test_db_session

    test_app.dependency_overrides[get_db] = override_db
    test_app.dependency_overrides[get_settings] = lambda: settings
    sink = test_app.state.development_mail_sink
    sink.clear()

    from httpx import ASGITransport

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
        headers={"Origin": "http://localhost:5173"},
    ) as client:
        for email in ("known@example.com", "unknown@example.com"):
            if email.startswith("known"):
                registration = await client.post(
                    "/api/v1/auth/register",
                    json={
                        "email": email,
                        "password": "SecurePassword123!",
                        "full_name": "Known",
                    },
                )
                assert registration.status_code == 201

        observed = {}
        for endpoint in (
            "/api/v1/auth/resend-verification",
            "/api/v1/auth/password-recovery",
        ):
            test_app.state.auth_recovery_rate_limiter.clear()
            for email in ("known@example.com", "unknown@example.com"):
                responses = []
                for attempt in range(3):
                    address = email.upper() if attempt == 1 else email
                    responses.append(
                        await client.post(endpoint, json={"email": address})
                    )
                observed[(endpoint, email)] = [
                    (response.status_code, response.json()) for response in responses
                ]

        for endpoint in (
            "/api/v1/auth/resend-verification",
            "/api/v1/auth/password-recovery",
        ):
            known = observed[(endpoint, "known@example.com")]
            unknown = observed[(endpoint, "unknown@example.com")]
            assert [status_code for status_code, _ in known] == [200, 200, 429]
            assert [status_code for status_code, _ in unknown] == [200, 200, 429]
            assert known[-1] == unknown[-1]
            assert known[-1][1] == {
                "detail": "If this address is eligible, instructions will be delivered."
            }


@pytest.mark.asyncio
async def test_email_limit_is_normalized_and_shared_across_recovery_routes(
    test_db_session: AsyncSession,
):
    settings = Settings(
        _env_file=None,
        app_env="local",
        deployment_environment="development",
        enable_local_mail_sink=True,
        auth_recovery_email_limit=2,
        auth_recovery_ip_limit=20,
        auth_recovery_rate_window_seconds=600,
    )
    test_app = create_app(settings)

    async def override_db():
        yield test_db_session

    test_app.dependency_overrides[get_db] = override_db
    test_app.dependency_overrides[get_settings] = lambda: settings

    from httpx import ASGITransport

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
        headers={"Origin": "http://localhost:5173"},
    ) as client:
        first = await client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "normalized@example.com"},
        )
        second = await client.post(
            "/api/v1/auth/password-recovery",
            json={"email": "NORMALIZED@example.com"},
        )
        third = await client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "normalized@example.com"},
        )
        assert [first.status_code, second.status_code, third.status_code] == [
            200,
            200,
            429,
        ]
        assert third.json() == {
            "detail": "If this address is eligible, instructions will be delivered."
        }
        limiter_keys = tuple(test_app.state.auth_recovery_rate_limiter._counts)
        assert limiter_keys
        assert all("normalized@example.com" not in key for key in limiter_keys)


@pytest.mark.asyncio
async def test_ip_limit_is_shared_across_recovery_routes_only(
    test_db_session: AsyncSession,
):
    settings = Settings(
        _env_file=None,
        app_env="local",
        deployment_environment="development",
        enable_local_mail_sink=True,
        auth_recovery_email_limit=10,
        auth_recovery_ip_limit=2,
        auth_recovery_rate_window_seconds=600,
    )
    test_app = create_app(settings)

    async def override_db():
        yield test_db_session

    test_app.dependency_overrides[get_db] = override_db
    test_app.dependency_overrides[get_settings] = lambda: settings

    from httpx import ASGITransport

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
        headers={"Origin": "http://localhost:5173"},
    ) as client:
        first = await client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "first@example.com"},
        )
        second = await client.post(
            "/api/v1/auth/password-recovery",
            json={"email": "second@example.com"},
        )
        limited = await client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "third@example.com"},
        )
        assert [first.status_code, second.status_code, limited.status_code] == [
            200,
            200,
            429,
        ]
        assert limited.json() == {
            "detail": "If this address is eligible, instructions will be delivered."
        }

        registration = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "unrelated@example.com",
                "password": "SecurePassword123!",
                "full_name": "Unrelated",
            },
        )
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "missing@example.com", "password": "not-a-password"},
        )
        assert registration.status_code == 201
        assert login.status_code == 401


@pytest.mark.asyncio
async def test_local_mail_tokens_are_recipient_bound_hashed_expiring_and_single_use(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    development_mail_sink,
):
    credentials = {
        "alice@example.com": "AlicePassword123!",
        "bob@example.com": "BobPassword123!",
    }
    registrations = {}
    for email, password in credentials.items():
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "full_name": email.split("@")[0],
            },
        )
        assert response.status_code == 201
        registrations[email] = response.json()

    verification_tokens = {}
    for email in credentials:
        message = development_mail_sink.consume_latest(email, "email-verification")
        assert message is not None
        assert message.recipient == email
        assert message.token is not None
        verification_tokens[email] = message.token
        record = await test_db_session.scalar(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == hash_token(message.token)
            )
        )
        assert record is not None
        assert str(record.user_id) == registrations[email]["user_id"]
        verification_lifetime = (
            record.expires_at - record.created_at
        ).total_seconds()
        assert 23 * 3600 <= verification_lifetime <= 24 * 3600
        assert message.expires_at > datetime.now(UTC)

    verify_alice = await async_client.post(
        "/api/v1/auth/verify-email",
        json={"token": verification_tokens["alice@example.com"]},
    )
    assert verify_alice.status_code == 200
    alice_verification_record = await test_db_session.scalar(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash
            == hash_token(verification_tokens["alice@example.com"])
        )
    )
    assert alice_verification_record is not None
    assert alice_verification_record.used_at is not None
    replay_verification = await async_client.post(
        "/api/v1/auth/verify-email",
        json={"token": verification_tokens["alice@example.com"]},
    )
    assert replay_verification.status_code == 400
    bob_login_before_verify = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "bob@example.com", "password": credentials["bob@example.com"]},
    )
    assert bob_login_before_verify.status_code == 403
    verify_bob = await async_client.post(
        "/api/v1/auth/verify-email",
        json={"token": verification_tokens["bob@example.com"]},
    )
    assert verify_bob.status_code == 200

    reset_tokens = {}
    for email in credentials:
        response = await async_client.post(
            "/api/v1/auth/password-recovery", json={"email": email}
        )
        assert response.status_code == 200
        message = development_mail_sink.consume_latest(email, "password-reset")
        assert message is not None
        assert message.recipient == email
        assert message.token is not None
        reset_tokens[email] = message.token
        record = await test_db_session.scalar(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == hash_token(message.token)
            )
        )
        assert record is not None
        assert str(record.user_id) == registrations[email]["user_id"]
        reset_lifetime = (record.expires_at - record.created_at).total_seconds()
        assert 55 * 60 <= reset_lifetime <= 60 * 60

    reset_alice = await async_client.post(
        "/api/v1/auth/password-reset",
        json={
            "token": reset_tokens["alice@example.com"],
            "new_password": "AliceNewPass123!",
        },
    )
    assert reset_alice.status_code == 200
    bob_reset_record = await test_db_session.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash
            == hash_token(reset_tokens["bob@example.com"])
        )
    )
    assert bob_reset_record is not None
    bob_reset_record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await test_db_session.commit()
    expired_bob_reset = await async_client.post(
        "/api/v1/auth/password-reset",
        json={
            "token": reset_tokens["bob@example.com"],
            "new_password": "BobNewPassword456!",
        },
    )
    assert expired_bob_reset.status_code == 400
    replay_reset = await async_client.post(
        "/api/v1/auth/password-reset",
        json={
            "token": reset_tokens["alice@example.com"],
            "new_password": "AnotherPass456!",
        },
    )
    assert replay_reset.status_code == 400
    alice_old_password = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "alice@example.com",
            "password": credentials["alice@example.com"],
        },
    )
    bob_old_password = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "bob@example.com", "password": credentials["bob@example.com"]},
    )
    assert alice_old_password.status_code == 401
    assert bob_old_password.status_code == 200


@pytest.mark.asyncio
async def test_expired_local_verification_mail_token_is_rejected(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    development_mail_sink,
):
    email = "expired-verification@example.com"
    registration = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePassword123!",
            "full_name": "Expired Verification",
        },
    )
    assert registration.status_code == 201
    token = _local_mail_token(
        development_mail_sink, email, "email-verification"
    )
    record = await test_db_session.scalar(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == hash_token(token)
        )
    )
    assert record is not None
    record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await test_db_session.commit()

    response = await async_client.post(
        "/api/v1/auth/verify-email", json={"token": token}
    )
    assert response.status_code == 400


def test_local_mail_sink_capture_expires_and_is_consumed_once():
    sink = DevelopmentMailSink()
    sink.capture("recipient@example.com", "password-reset", "opaque-token", 60)

    message = sink.consume_latest("recipient@example.com", "password-reset")
    assert message is not None and message.token == "opaque-token"
    assert sink.consume_latest("recipient@example.com", "password-reset") is None

    sink.capture("recipient@example.com", "password-reset", "expired-token", -1)
    assert sink.consume_latest("recipient@example.com", "password-reset") is None
    assert sink.messages == []


@pytest.mark.asyncio
async def test_local_mail_sink_is_disabled_by_default_even_with_local_app_env():
    settings = Settings(_env_file=None, app_env="local")
    test_app = create_app(settings)
    assert test_app.state.development_mail_sink is None
    assert not settings.is_local_mail_sink_enabled


@pytest.mark.asyncio
async def test_local_sink_is_not_enabled_by_production_environment_even_with_opt_in():
    settings = Settings(
        _env_file=None, app_env="production", enable_local_mail_sink=True
    )
    test_app = create_app(settings)
    assert test_app.state.development_mail_sink is None
    assert not settings.is_local_mail_sink_enabled

    from httpx import ASGITransport

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        for path in (
            "/api/v1/auth/dev/verification-token",
            "/api/v1/auth/dev/password-reset-token",
        ):
            response = await client.post(path, json={"email": "anyone@example.com"})
            assert response.status_code == 404


@pytest.mark.asyncio
async def test_local_app_env_and_sink_opt_in_still_require_development_deployment():
    with pytest.raises(ValidationError, match="APP_ENV=local"):
        Settings(
            _env_file=None,
            app_env="local",
            enable_local_mail_sink=True,
            deployment_environment="production",
        )


@pytest.mark.asyncio
async def test_auth_tokens_are_not_written_to_application_logs(
    async_client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
    development_mail_sink,
):
    caplog.set_level(logging.INFO, logger="sandeshvani.auth")

    registration = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "token-check@example.com",
            "password": "SecurePassword123!",
            "full_name": "Token Check",
        },
    )
    assert registration.status_code == 201
    verification_token = _local_mail_token(
        development_mail_sink, "token-check@example.com", "email-verification"
    )

    resend = await async_client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "token-check@example.com"},
    )
    assert "dev_token" not in resend.json()
    resend_token = _local_mail_token(
        development_mail_sink, "token-check@example.com", "email-verification"
    )

    recovery = await async_client.post(
        "/api/v1/auth/password-recovery",
        json={"email": "token-check@example.com"},
    )
    assert "dev_token" not in recovery.json()
    recovery_token = _local_mail_token(
        development_mail_sink, "token-check@example.com", "password-reset"
    )

    issued_tokens = [verification_token, resend_token, recovery_token]
    assert all(issued_tokens)
    assert all(
        token not in record.getMessage()
        for token in issued_tokens
        for record in caplog.records
    ), "an authentication token was written to application logs"


@pytest.mark.asyncio
async def test_email_verification_and_unverified_login(
    async_client: AsyncClient,
    development_mail_sink,
):
    reg_payload = {
        "email": "teacher@university.edu.in",
        "password": "CollegePassword987!",
        "full_name": "Priya Sharma",
    }
    reg_res = await async_client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    token = _local_mail_token(
        development_mail_sink, reg_payload["email"], "email-verification"
    )

    # Attempt login before verification -> 403
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": reg_payload["email"], "password": reg_payload["password"]},
    )
    assert login_res.status_code == 403
    assert "not verified" in login_res.json()["detail"].lower()

    # Verify with invalid token -> 400
    invalid_verify = await async_client.post(
        "/api/v1/auth/verify-email", json={"token": "invalid_token_123"}
    )
    assert invalid_verify.status_code == 400

    # Verify with correct token -> 200
    verify_res = await async_client.post(
        "/api/v1/auth/verify-email", json={"token": token}
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "active"

    # Login after verification -> 200
    login_res2 = await async_client.post(
        "/api/v1/auth/login",
        json={"email": reg_payload["email"], "password": reg_payload["password"]},
    )
    assert login_res2.status_code == 200
    login_data = login_res2.json()
    assert "access_token" in login_data
    assert "csrf_token" in login_data
    assert "sandeshvani_refresh" in login_res2.cookies


@pytest.mark.asyncio
async def test_refresh_token_rotation_and_reuse_detection(
    async_client: AsyncClient,
    development_mail_sink,
):
    # Setup registered & verified user
    email = "admin@district.gov.in"
    password = "AdminSecret2026!"
    await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "District Admin"},
    )
    token = _local_mail_token(
        development_mail_sink, email, "email-verification"
    )
    await async_client.post("/api/v1/auth/verify-email", json={"token": token})

    # Initial login
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    first_refresh = login_res.cookies.get("sandeshvani_refresh")
    assert first_refresh is not None

    # 1. Normal rotation
    async_client.cookies.set("sandeshvani_refresh", first_refresh)
    rot_res = await async_client.post("/api/v1/auth/refresh")
    assert rot_res.status_code == 200
    second_refresh = rot_res.cookies.get("sandeshvani_refresh")
    assert second_refresh is not None
    assert second_refresh != first_refresh

    # 2. Token reuse attack: Presenting the already-rotated first_refresh!
    async_client.cookies.set("sandeshvani_refresh", first_refresh)
    attack_res = await async_client.post("/api/v1/auth/refresh")
    assert attack_res.status_code == 401
    assert "reuse detected" in attack_res.json()["detail"].lower()

    # 3. Verify that second_refresh is also dead (entire family was revoked)
    async_client.cookies.set("sandeshvani_refresh", second_refresh)
    post_attack = await async_client.post("/api/v1/auth/refresh")
    assert post_attack.status_code == 401


@pytest.mark.asyncio
async def test_logout_and_logout_all(
    async_client: AsyncClient,
    development_mail_sink,
):
    email = "staff@hospital.org.in"
    password = "HospitalPassword123!"
    reg_res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Hospital Staff"},
    )
    assert reg_res.status_code == 201
    token = _local_mail_token(development_mail_sink, email, "email-verification")
    await async_client.post("/api/v1/auth/verify-email", json={"token": token})

    login_res = await async_client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    access_token = login_res.json()["access_token"]
    refresh_token = login_res.cookies.get("sandeshvani_refresh")
    assert refresh_token is not None

    # Logout
    async_client.cookies.set("sandeshvani_refresh", refresh_token)
    logout_res = await async_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_res.status_code == 200

    # Refresh should now fail
    async_client.cookies.set("sandeshvani_refresh", refresh_token)
    ref_res = await async_client.post("/api/v1/auth/refresh")
    assert ref_res.status_code == 401


@pytest.mark.asyncio
async def test_password_reset_flow(
    async_client: AsyncClient,
    development_mail_sink,
):
    email = "citizen@service.in"
    password = "OldPassword123!"
    new_password = "BrandNewPassword456!"

    reg_res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Citizen User"},
    )
    assert reg_res.status_code == 201
    verify_token = _local_mail_token(
        development_mail_sink, email, "email-verification"
    )
    await async_client.post("/api/v1/auth/verify-email", json={"token": verify_token})

    # Request password recovery
    req_res = await async_client.post(
        "/api/v1/auth/password-recovery", json={"email": email}
    )
    assert req_res.status_code == 200
    assert "dev_token" not in req_res.json()
    reset_token = _local_mail_token(
        development_mail_sink, email, "password-reset"
    )
    assert reset_token is not None

    # Confirm password reset
    confirm_res = await async_client.post(
        "/api/v1/auth/password-reset",
        json={"token": reset_token, "new_password": new_password},
    )
    assert confirm_res.status_code == 200
    replay_res = await async_client.post(
        "/api/v1/auth/password-reset",
        json={"token": reset_token, "new_password": "AnotherPassword789!"},
    )
    assert replay_res.status_code == 400

    # Login with old password fails
    old_login = await async_client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert old_login.status_code == 401

    # Login with new password succeeds
    new_login = await async_client.post(
        "/api/v1/auth/login", json={"email": email, "password": new_password}
    )
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_suspended_user_rejection(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    development_mail_sink,
):
    email = "suspended@agency.gov.in"
    password = "Password123!"

    reg_res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Suspended Officer"},
    )
    assert reg_res.status_code == 201
    verify_token = _local_mail_token(
        development_mail_sink, email, "email-verification"
    )
    await async_client.post("/api/v1/auth/verify-email", json={"token": verify_token})

    # Suspend user directly in DB
    from sqlalchemy import update

    await test_db_session.execute(
        update(User).where(User.email == email).values(status="suspended")
    )
    await test_db_session.commit()

    # Login attempt should yield 403
    login_res = await async_client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert login_res.status_code == 403
    assert "suspended" in login_res.json()["detail"].lower()
