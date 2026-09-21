import importlib.util
import logging
import os
import re
import time
from collections import OrderedDict, deque
from contextlib import asynccontextmanager

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, Response
from starlette.routing import Mount, Route
from starlette.types import ASGIApp, Receive, Scope, Send

from api import WellnessClient
from api.config import Settings, create_http_client
from server import mcp
from services import WellnessService, configure_service

SETTINGS = Settings.from_env()
HTTP_CLIENT = create_http_client()
configure_service(WellnessService(WellnessClient(SETTINGS.api_key, HTTP_CLIENT)))

# ── Fix 2: Redact serviceKey from all uvicorn log records ─────────────────────
# The full upstream URL (including serviceKey=...) can appear in uvicorn access
# and error logs.  This filter replaces the key value with [REDACTED] before
# any log handler writes it.
_KEY_RE = re.compile(r"(serviceKey=)[^&\s\"']+", re.IGNORECASE)


class _RedactKeyFilter(logging.Filter):
    def __init__(self, api_key: str) -> None:
        super().__init__()
        self.api_key = api_key

    def filter(self, record: logging.LogRecord) -> bool:
        message = _KEY_RE.sub(r"\1[REDACTED]", record.getMessage())
        if self.api_key:
            message = message.replace(self.api_key, "[REDACTED]")
        record.msg = message
        record.args = ()
        return True


_redaction_filter = _RedactKeyFilter(SETTINGS.api_key)
for _logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error", "httpx", "services"):
    logging.getLogger(_logger_name).addFilter(_redaction_filter)


# ── Fix 4: Per-IP rate limiter on /mcp ───────────────────────────────────────
# Limits each IP to _RATE_MAX requests per _RATE_WINDOW seconds on the /mcp
# endpoint, protecting the 1,000 req/day upstream quota from exhaustion.
_RATE_WINDOW = 60   # seconds
_RATE_MAX    = 60   # requests per window per IP (1 req/s average — plenty for agents)
_MAX_TRACKED_CLIENTS = 10_000
_rate_store: OrderedDict[str, deque] = OrderedDict()


class RateLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope.get("path", "").startswith("/mcp"):
            client = scope.get("client")
            ip = client[0] if client else "unknown"
            now = time.monotonic()
            if ip not in _rate_store and len(_rate_store) >= _MAX_TRACKED_CLIENTS:
                _rate_store.popitem(last=False)
            window = _rate_store.setdefault(ip, deque())
            _rate_store.move_to_end(ip)
            while window and now - window[0] > _RATE_WINDOW:
                window.popleft()
            if len(window) >= _RATE_MAX:
                resp = Response(
                    "Too Many Requests",
                    status_code=429,
                    headers={"Retry-After": str(_RATE_WINDOW)},
                )
                await resp(scope, receive, send)
                return
            window.append(now)
        await self.app(scope, receive, send)


# ── Fix 1: Security response headers ─────────────────────────────────────────
# Sets hardened HTTP headers on every response:
#   - X-Content-Type-Options prevents MIME-type sniffing
#   - X-Frame-Options blocks clickjacking on the landing page
#   - Referrer-Policy limits referrer leakage
#   - Content-Security-Policy restricts resource origins
_CSP = (
    "default-src 'self'; "
    "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data: https:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'"
)

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": _CSP,
}


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
                for k, v in _SECURITY_HEADERS.items():
                    headers[k.lower().encode()] = v.encode()
                message = {**message, "headers": list(headers.items())}
            await send(message)

        await self.app(scope, receive, send_with_headers)


# ── Route handlers ─────────────────────────────────────────────────────────────
_STATIC = os.path.join(os.path.dirname(__file__), "static")


async def serve_index(request: Request) -> FileResponse:
    return FileResponse(os.path.join(_STATIC, "index.html"))


async def serve_favicon(request: Request) -> FileResponse:
    return FileResponse(os.path.join(_STATIC, "favicon.png"), media_type="image/png")


# Build the streamable HTTP app (lazily initialises the session manager).
mcp_http_app = mcp.streamable_http_app()


# ── Fix 6: Clean HTTP client shutdown ─────────────────────────────────────────
@asynccontextmanager
async def lifespan(app):
    try:
        async with mcp.session_manager.run():
            yield
    finally:
        # Close the shared upstream HTTP connection pool on every shutdown path.
        if not HTTP_CLIENT.is_closed:
            await HTTP_CLIENT.aclose()


app = Starlette(
    routes=[
        Route("/", endpoint=serve_index),
        Route("/favicon.png", endpoint=serve_favicon),
        Mount("/", app=mcp_http_app),
    ],
    lifespan=lifespan,
)

app = SecurityHeadersMiddleware(app)
app = RateLimitMiddleware(app)

if __name__ == "__main__":
    # Fix 7: Use uvloop when available — 2-4x faster event loop for I/O workloads.
    _loop = "uvloop" if importlib.util.find_spec("uvloop") else "asyncio"
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=SETTINGS.port,
        loop=_loop,
        access_log=True,
    )
