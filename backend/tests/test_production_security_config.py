import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException, Response
from pydantic import ValidationError
from starlette.requests import Request

from app.api.deps import verify_origin
from app.api.v1.auth import _set_refresh_cookie
from app.core.config import Settings
from app.main import create_app


def _production_settings(**overrides: object) -> Settings:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    defaults: dict[str, object] = {
        "_env_file": None,
        "app_env": "production",
        "deployment_environment": "production",
        "jwt_private_key_pem": private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode(),
        "jwt_public_key_pem": private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode(),
        "csrf_secret": "x" * 32,
        "cookie_secure": True,
        "allowed_origins": ["https://app.sandeshvani.in"],
    }
    defaults.update(overrides)
    return Settings(**defaults)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"jwt_private_key_pem": ""}, "JWT private and public keys"),
        ({"csrf_secret": "change-me"}, "CSRF_SECRET"),
        ({"cookie_secure": False}, "COOKIE_SECURE"),
        ({"allowed_origins": ["http://app.sandeshvani.in"]}, "ALLOWED_ORIGINS"),
    ],
)
def test_production_rejects_unsafe_configuration(
    overrides: dict[str, object], message: str
):
    with pytest.raises(ValidationError, match=message):
        _production_settings(**overrides)


def test_production_accepts_valid_configuration_and_uses_strict_cors():
    settings = _production_settings()
    app = create_app(settings)
    cors = next(m for m in app.user_middleware if m.cls.__name__ == "CORSMiddleware")
    assert cors.kwargs["allow_origins"] == ["https://app.sandeshvani.in"]
    assert cors.kwargs["allow_methods"] == [
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ]
    assert "*" not in cors.kwargs["allow_headers"]


def test_samesite_none_requires_secure_cookie_in_every_environment():
    with pytest.raises(ValidationError, match="SameSite=None"):
        Settings(
            _env_file=None,
            app_env="local",
            deployment_environment="development",
            cookie_samesite="none",
            cookie_secure=False,
        )


def test_refresh_cookie_uses_configured_security_flags():
    response = Response()
    settings = Settings(
        _env_file=None,
        app_env="local",
        deployment_environment="development",
        cookie_secure=True,
        cookie_samesite="strict",
        cookie_domain="auth.sandeshvani.in",
    )
    _set_refresh_cookie(response, "opaque-refresh-token", settings)
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=strict" in cookie
    assert "Domain=auth.sandeshvani.in" in cookie
    assert "Path=/api/v1/auth" in cookie


def test_referer_must_match_an_exact_allowed_origin():
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "http",
            "server": ("test", 80),
            "path": "/api/v1/auth/login",
            "headers": [(b"referer", b"http://localhost:5173.attacker.example/path")],
        }
    )
    with pytest.raises(HTTPException, match="Forbidden cross-origin referer"):
        verify_origin(request)
