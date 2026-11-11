import time
from datetime import timedelta

import pytest
from jwt.exceptions import ExpiredSignatureError, InvalidSignatureError

from app.core.security import (
    EdDSATokenSigner,
    RS256TokenSigner,
    create_access_token,
    create_csrf_token,
    hash_password,
    hash_token,
    verify_access_token,
    verify_csrf_token,
    verify_password,
)


def test_argon2id_password_hashing():
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$argon2id$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_opaque_token_hashing():
    raw_token = "opaque_token_value_abc123"
    hashed = hash_token(raw_token)

    assert len(hashed) == 64
    assert hash_token(raw_token) == hashed
    assert hash_token("different") != hashed


def test_rs256_asymmetric_signer():
    signer = RS256TokenSigner()
    claims = {
        "sub": "user-123",
        "session_id": "session-123",
        "jti": "jti-123",
        "iat": int(time.time()),
        "org_id": "org-456",
        "exp": int(time.time()) + 300,
        "iss": "sandeshvani-api",
        "aud": "sandeshvani-api",
    }

    token = signer.sign(claims)
    assert isinstance(token, str)

    payload = signer.verify(token)
    assert payload["sub"] == "user-123"
    assert payload["org_id"] == "org-456"

    # Verify signature fails with wrong key
    other_signer = RS256TokenSigner()
    with pytest.raises(InvalidSignatureError):
        other_signer.verify(token)


def test_eddsa_asymmetric_signer():
    signer = EdDSATokenSigner()
    claims = {
        "sub": "user-eddsa",
        "session_id": "session-eddsa",
        "jti": "jti-eddsa",
        "iat": int(time.time()),
        "exp": int(time.time()) + 300,
        "iss": "sandeshvani-api",
        "aud": "sandeshvani-api",
    }

    token = signer.sign(claims)
    assert isinstance(token, str)

    payload = signer.verify(token)
    assert payload["sub"] == "user-eddsa"

    other_signer = EdDSATokenSigner()
    with pytest.raises(InvalidSignatureError):
        other_signer.verify(token)


def test_access_token_creation_and_expiration():
    token = create_access_token(
        user_id="user-xyz",
        session_id="session-xyz",
        org_id="org-xyz",
        expires_delta=timedelta(seconds=-1),  # Expired immediately
    )
    with pytest.raises(ExpiredSignatureError):
        verify_access_token(token)


def test_csrf_token_validation():
    session_id = "sess-12345"
    token = create_csrf_token(session_id)

    assert verify_csrf_token(token, session_id) is True
    assert verify_csrf_token(token, "different-session") is False
    assert verify_csrf_token("invalid:token:format", session_id) is False
