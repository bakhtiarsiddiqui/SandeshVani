"""Service-to-service API key authentication for AI endpoints.

Uses constant-time comparison (secrets.compare_digest) to prevent timing attacks.
The key is loaded once from AISettings and never echoed in responses or logs.
"""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from ai.config import AISettings, get_ai_settings

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(
    api_key: Annotated[str | None, Security(_API_KEY_HEADER)],
    ai_settings: Annotated[AISettings, Depends(get_ai_settings)],
) -> None:
    """FastAPI dependency that rejects requests missing a valid X-API-Key header.

    Raises HTTP 401 when the header is absent or HTTP 403 when the value is wrong.
    Uses constant-time comparison to avoid timing-based key enumeration.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header is required for AI endpoints",
        )
    expected = ai_settings.ai_service_api_key
    if not secrets.compare_digest(api_key.encode(), expected.encode()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
