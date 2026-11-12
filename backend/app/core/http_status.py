"""Compatibility aliases for HTTP status codes across supported Starlette versions."""

# Starlette renamed the 422 constant. Keep the numeric code stable across
# supported FastAPI/Starlette combinations without importing a deprecated alias.
HTTP_422_UNPROCESSABLE_CONTENT = 422
