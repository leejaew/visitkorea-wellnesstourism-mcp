from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from mcp_server.clients import SharedState

RATE_WINDOW_SECONDS = 60
RATE_MAX_REQUESTS = 60

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data: https:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'"
)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
}


class RateLimitMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        shared_state: SharedState,
        max_requests: int = RATE_MAX_REQUESTS,
        window_seconds: int = RATE_WINDOW_SECONDS,
    ) -> None:
        self.app = app
        self.shared_state = shared_state
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope.get("path", "").startswith("/mcp"):
            client = scope.get("client")
            client_id = client[0] if client else "unknown"
            request_count = await self.shared_state.increment_rate_limit(
                client_id, self.window_seconds
            )
            if request_count > self.max_requests:
                response = Response(
                    "Too Many Requests",
                    status_code=429,
                    headers={"Retry-After": str(self.window_seconds)},
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                for name, value in SECURITY_HEADERS.items():
                    headers[name.lower().encode()] = value.encode()
                message = {**message, "headers": list(headers.items())}
            await send(message)

        await self.app(scope, receive, send_with_headers)