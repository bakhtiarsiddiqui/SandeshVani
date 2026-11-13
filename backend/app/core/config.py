from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_CSRF_SECRETS = {
    "",
    "change-me",
    "changeme",
    "dev_csrf_secret_32_bytes_minimum_key_change_in_prod",
}


def _as_asyncpg_url(database_url: str) -> str:
    """Normalize Render's standard PostgreSQL URL for SQLAlchemy async engines."""
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return database_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SandeshVani"
    app_env: str = "production"
    deployment_environment: Literal["development", "production"] = "production"
    enable_local_mail_sink: bool = False
    dev_mail_smtp_host: str = ""
    dev_mail_smtp_port: int = Field(default=1025, gt=0, le=65535)
    dev_mail_smtp_starttls: bool = False
    dev_mail_smtp_username: str = ""
    dev_mail_smtp_password: str = ""
    dev_mail_from: str = "no-reply@sandeshvani.local"
    auth_recovery_email_limit: int = Field(default=5, gt=0)
    auth_recovery_ip_limit: int = Field(default=30, gt=0)
    auth_recovery_rate_window_seconds: int = Field(default=900, gt=0)
    audience_import_storage_dir: Path = Path("./var/private/audience-imports")
    audience_import_max_bytes: int = Field(default=25 * 1024 * 1024, gt=0)
    audience_import_max_rows: int = Field(default=100_000, gt=0)
    api_v1_prefix: str = "/api/v1"
    version: str = "0.1.0"

    database_url: str = ""
    postgres_db: str = "sandeshvani"
    postgres_user: str = "sandeshvani_app"
    postgres_password: str = "local_dev_change_me"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    migration_database_url: str = ""
    migration_database_role: str = ""

    redis_url: str = "redis://localhost:6379/0"

    jwt_algorithm: str = "RS256"
    jwt_private_key_pem: str = ""
    jwt_public_key_pem: str = ""
    jwt_issuer: str = "sandeshvani-api"
    jwt_audience: str = "sandeshvani-api"
    access_token_expire_minutes: int = 10
    refresh_token_expire_days: int = 7

    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    cookie_domain: str | None = None
    csrf_secret: str = "dev_csrf_secret_32_bytes_minimum_key_change_in_prod"

    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    @model_validator(mode="after")
    def validate_security_configuration(self):
        self.jwt_algorithm = self.jwt_algorithm.upper()
        self.cookie_samesite = self.cookie_samesite.lower()
        if self.jwt_algorithm not in {"RS256", "EDDSA"}:
            raise ValueError("JWT_ALGORITHM must be RS256 or EdDSA")
        if self.cookie_samesite not in {"lax", "strict", "none"}:
            raise ValueError("COOKIE_SAMESITE must be lax, strict, or none")
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError("SameSite=None cookies require COOKIE_SECURE=true")
        if self.deployment_environment == "production":
            if self.app_env == "local":
                raise ValueError("APP_ENV=local is not allowed in production")
            self._validate_jwt_key_pair()
            if (
                self.csrf_secret.strip().lower() in _INSECURE_CSRF_SECRETS
                or len(self.csrf_secret.encode()) < 32
            ):
                raise ValueError(
                    "CSRF_SECRET must be a configured secret of at least 32 bytes "
                    "in production"
                )
            if not self.cookie_secure:
                raise ValueError(
                    "Production cookies require COOKIE_SECURE=true and a valid "
                    "COOKIE_SAMESITE policy"
                )
            self._validate_production_origins()
            if self.enable_local_mail_sink:
                raise ValueError(
                    "ENABLE_LOCAL_MAIL_SINK must be disabled in production"
                )
        return self

    def _validate_jwt_key_pair(self) -> None:
        if not self.jwt_private_key_pem.strip() or not self.jwt_public_key_pem.strip():
            raise ValueError("JWT private and public keys are required in production")
        try:
            private_key = serialization.load_pem_private_key(
                self.jwt_private_key_pem.encode("utf-8"), password=None
            )
            public_key = serialization.load_pem_public_key(
                self.jwt_public_key_pem.encode("utf-8")
            )
        except (TypeError, ValueError) as err:
            raise ValueError("JWT signing keys are not valid PEM keys") from err

        if self.jwt_algorithm == "RS256":
            expected_type = rsa.RSAPrivateKey
            expected_public_type = rsa.RSAPublicKey
        else:
            expected_type = ed25519.Ed25519PrivateKey
            expected_public_type = ed25519.Ed25519PublicKey
        if not isinstance(private_key, expected_type) or not isinstance(
            public_key, expected_public_type
        ):
            raise ValueError("JWT signing keys do not match JWT_ALGORITHM")
        if self.jwt_algorithm == "RS256" and private_key.key_size < 2048:
            raise ValueError("RS256 private key must be at least 2048 bits")
        derived_public = private_key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        configured_public = public_key.public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        if derived_public != configured_public:
            raise ValueError("JWT private and public keys are not a matching pair")

    def _validate_production_origins(self) -> None:
        if not self.allowed_origins:
            raise ValueError(
                "ALLOWED_ORIGINS must contain at least one HTTPS origin in production"
            )
        for origin in self.allowed_origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme != "https"
                or not parsed.netloc
                or parsed.username
                or parsed.password
                or parsed.path not in ("", "/")
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(
                    "ALLOWED_ORIGINS must contain exact HTTPS origins in production"
                )

    @property
    def is_local_development(self) -> bool:
        return self.app_env == "local"

    @property
    def is_local_mail_sink_enabled(self) -> bool:
        return (
            self.deployment_environment == "development"
            and self.is_local_development
            and self.enable_local_mail_sink
        )

    def get_database_url(self) -> str:
        """Return the restricted runtime database URL with an async driver."""
        if self.database_url:
            return _as_asyncpg_url(self.database_url)

        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    def get_migration_database_url(self) -> str:
        """Return the dedicated Alembic migration URL with an async driver."""
        if not self.migration_database_url:
            raise ValueError("MIGRATION_DATABASE_URL must be configured for Alembic")

        return _as_asyncpg_url(self.migration_database_url)

    def get_migration_database_role(self) -> str | None:
        role = self.migration_database_role.strip()
        if not role:
            return None
        if not role.replace("_", "").isalnum() or role[0].isdigit():
            raise ValueError(
                "MIGRATION_DATABASE_ROLE must be a simple PostgreSQL role name"
            )
        return role


@lru_cache
def get_settings() -> Settings:
    return Settings()
