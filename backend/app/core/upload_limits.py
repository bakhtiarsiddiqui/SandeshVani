from starlette.responses import JSONResponse


class _RequestBodyTooLarge(Exception):
    pass


class AudienceUploadBodyLimitMiddleware:
    """Bound multipart request bytes before Starlette spools uploaded files."""

    def __init__(self, app, upload_path: str, max_body_bytes: int):
        self.app = app
        self.upload_path = upload_path
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] != "http"
            or scope.get("method") != "POST"
            or scope.get("path") != self.upload_path
        ):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                declared_length = int(content_length)
            except ValueError:
                declared_length = None
            if declared_length is not None and declared_length > self.max_body_bytes:
                response = JSONResponse(
                    {"detail": "Audience upload request exceeds the configured limit"},
                    status_code=413,
                )
                await response(scope, receive, send)
                return

        received_bytes = 0

        async def limited_receive():
            nonlocal received_bytes
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self.max_body_bytes:
                    raise _RequestBodyTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _RequestBodyTooLarge:
            response = JSONResponse(
                {"detail": "Audience upload request exceeds the configured limit"},
                status_code=413,
            )
            await response(scope, receive, send)
