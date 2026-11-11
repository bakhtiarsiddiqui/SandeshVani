import hashlib
import hmac
import secrets
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa

from app.core.config import get_settings

# Argon2id password hasher with secure defaults
_ph = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
)


def ensure_utc(dt: datetime | None) -> datetime | None:
    """Ensure datetime is timezone-aware in UTC (robust against SQLite)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against an Argon2id hash."""
    try:
        return _ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, Exception):
        return False


def hash_token(token: str) -> str:
    """Hash opaque tokens (refresh, reset, verification) with SHA-256 for DB."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random opaque token."""
    return secrets.token_urlsafe(length)


class BaseTokenSigner(ABC):
    """Abstract interface for asymmetric JWT signing.

    The choice between RS256 and EdDSA is configurable pending key-management
    review. Both provide asymmetric signing so verification does not expose
    signing keys.
    """

    @abstractmethod
    def sign(self, claims: dict[str, Any]) -> str:
        pass

    @abstractmethod
    def verify(self, token: str) -> dict[str, Any]:
        pass

    @property
    @abstractmethod
    def algorithm(self) -> str:
        pass


class RS256TokenSigner(BaseTokenSigner):
    def __init__(
        self,
        private_key_pem: str | None = None,
        public_key_pem: str | None = None,
    ):
        if private_key_pem and public_key_pem:
            self._private_key = serialization.load_pem_private_key(
                private_key_pem.encode("utf-8"), password=None
            )
            self._public_key = serialization.load_pem_public_key(
                public_key_pem.encode("utf-8")
            )
        else:
            # Generate 2048-bit RSA key pair for local/test if not configured
            self._private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            self._public_key = self._private_key.public_key()

    @property
    def algorithm(self) -> str:
        return "RS256"

    def sign(self, claims: dict[str, Any]) -> str:
        return jwt.encode(claims, self._private_key, algorithm="RS256")

    def verify(self, token: str) -> dict[str, Any]:
        settings = get_settings()
        return jwt.decode(
            token,
            self._public_key,
            algorithms=["RS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "sub", "session_id", "jti"]},
        )


class EdDSATokenSigner(BaseTokenSigner):
    def __init__(
        self,
        private_key_pem: str | None = None,
        public_key_pem: str | None = None,
    ):
        if private_key_pem and public_key_pem:
            self._private_key = serialization.load_pem_private_key(
                private_key_pem.encode("utf-8"), password=None
            )
            self._public_key = serialization.load_pem_public_key(
                public_key_pem.encode("utf-8")
            )
        else:
            # Generate Ed25519 key pair for local/test if not configured
            self._private_key = ed25519.Ed25519PrivateKey.generate()
            self._public_key = self._private_key.public_key()

    @property
    def algorithm(self) -> str:
        return "EdDSA"

    def sign(self, claims: dict[str, Any]) -> str:
        return jwt.encode(claims, self._private_key, algorithm="EdDSA")

    def verify(self, token: str) -> dict[str, Any]:
        settings = get_settings()
        return jwt.decode(
            token,
            self._public_key,
            algorithms=["EdDSA"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "sub", "session_id", "jti"]},
        )


_token_signer: BaseTokenSigner | None = None


def get_token_signer() -> BaseTokenSigner:
    global _token_signer
    if _token_signer is None:
        settings = get_settings()
        algo = settings.jwt_algorithm.upper()
        if algo == "EDDSA":
            _token_signer = EdDSATokenSigner(
                private_key_pem=settings.jwt_private_key_pem or None,
                public_key_pem=settings.jwt_public_key_pem or None,
            )
        elif algo == "RS256":
            _token_signer = RS256TokenSigner(
                private_key_pem=settings.jwt_private_key_pem or None,
                public_key_pem=settings.jwt_public_key_pem or None,
            )
        else:
            raise ValueError("JWT_ALGORITHM must be RS256 or EdDSA")
    return _token_signer


def create_access_token(
    user_id: str,
    session_id: str,
    org_id: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a short-lived asymmetric JWT with minimal claims (10 min lifetime)."""
    settings = get_settings()
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    claims: dict[str, Any] = {
        "sub": user_id,
        "session_id": session_id,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    if org_id:
        claims["org_id"] = org_id

    signer = get_token_signer()
    return signer.sign(claims)


def verify_access_token(token: str) -> dict[str, Any]:
    """Verify signature and expiration of an access token."""
    signer = get_token_signer()
    return signer.verify(token)


def create_csrf_token(session_id: str) -> str:
    """Generate a HMAC double-submit CSRF token bound to the session."""
    settings = get_settings()
    message = f"{session_id}:{secrets.token_hex(32)}"
    sig = hmac.new(
        settings.csrf_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return f"{message}:{sig}"


def verify_csrf_token(csrf_token: str, expected_session_id: str) -> bool:
    """Verify the validity of a CSRF token for a given session."""
    settings = get_settings()
    try:
        parts = csrf_token.split(":")
        if len(parts) != 3:
            return False
        session_id, nonce, signature = parts
        if session_id != expected_session_id:
            return False
        expected_sig = hmac.new(
            settings.csrf_secret.encode("utf-8"),
            f"{session_id}:{nonce}".encode(),
            hashlib.sha256,
        ).hexdigest()
        return secrets.compare_digest(signature, expected_sig)
    except Exception:
        return False
