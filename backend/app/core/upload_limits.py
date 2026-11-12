from starlette.responses import JSONResponse


class AudienceUploadBodyLimitMiddleware:
    """Bound and buffer upload requests before Starlette parses multipart data."""

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

        # Consume the body before calling Starlette's multipart parser. Raising
        # from receive() is not reliable here: Starlette may translate parser
        # exceptions into HTTP 400. This bounded buffer makes the limit apply
        # consistently to both Content-Length and chunked requests.
        buffered_messages = []
        received_bytes = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                buffered_messages.append(message)
                break
            if message["type"] != "http.request":
                buffered_messages.append(message)
                continue

            received_bytes += len(message.get("body", b""))
            if received_bytes > self.max_body_bytes:
                response = JSONResponse(
                    {"detail": "Audience upload request exceeds the configured limit"},
                    status_code=413,
                )
                await response(scope, receive, send)
                return

            buffered_messages.append(message)
            if not message.get("more_body", False):
                break

        async def replay_receive():
            if buffered_messages:
                return buffered_messages.pop(0)
            return {"type": "http.disconnect"}

        await self.app(scope, replay_receive, send)
