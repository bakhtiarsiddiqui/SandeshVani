"""Compatibility aliases for HTTP status codes across supported Starlette versions."""

from fastapi import status


# Starlette 0.48 renamed the 422 constant. FastAPI's minimum supported release
# can still resolve an older Starlette, so use the stable numeric code as fallback.
HTTP_422_UNPROCESSABLE_CONTENT = getattr(
    status, "HTTP_422_UNPROCESSABLE_CONTENT", 422
)
