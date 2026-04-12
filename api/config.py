from typing import Optional

import httpx

# HTTPS enforced: the serviceKey travels as a query param; plain HTTP would
# expose it to any observer on the network path.
BASE_URL = "https://apis.data.go.kr/B551011/WellnessTursmService"

TIMEOUT = httpx.Timeout(
    connect=10.0,   # TCP + TLS handshake
    read=25.0,      # waiting for the first byte
    write=5.0,
    pool=5.0,       # time to acquire a connection from the pool
)

# One persistent AsyncClient reused across all tool calls.
# Eliminates per-call TCP + TLS handshake overhead (~100–300 ms each).
_LIMITS = httpx.Limits(
    max_connections=10,
    max_keepalive_connections=5,
    keepalive_expiry=30,
)

_http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=TIMEOUT, limits=_LIMITS)
    return _http_client
