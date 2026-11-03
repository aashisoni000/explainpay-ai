from starlette.formparsers import MultiPartParser
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import get_settings

# Accepted multipart bodies remain in memory. The middleware rejects larger bodies
# before Starlette can spool an uploaded raw CSV to a temporary file.
MULTIPART_OVERHEAD = 64 * 1024
MultiPartParser.spool_max_size = 50 * 1024 * 1024 + MULTIPART_OVERHEAD


class UploadBodyLimit:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] != "/api/transactions/upload":
            await self.app(scope, receive, send)
            return
        limit = get_settings().max_upload_bytes + MULTIPART_OVERHEAD
        parts = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > limit:
                await JSONResponse(
                    {"detail": "Multipart upload exceeds the configured size limit"}, status_code=413
                )(scope, receive, send)
                return
            parts.append(chunk)
            if not message.get("more_body", False):
                break
        body = b"".join(parts)
        replayed = False

        async def replay():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay, send)
