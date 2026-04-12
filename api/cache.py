import asyncio
import time
from typing import Optional

# Avoids hitting the 1,000 req/day upstream quota for identical repeated calls.
# District codes cached for 1 h (change at most daily).
# All other endpoints cached for 5 min.
_CACHE: dict[str, tuple[dict, float]] = {}
_TTL_SHORT = 300.0    # 5 minutes — search / detail results
_TTL_LONG  = 3600.0   # 1 hour    — district code lookups

# Per-key asyncio locks prevent cache stampede: without them, N concurrent
# requests for the same uncached key would all fire upstream simultaneously
# before any one populates the cache, wasting the daily quota.
_FETCH_LOCKS: dict[str, asyncio.Lock] = {}


def cache_key(endpoint: str, params: dict) -> str:
    """Build a cache key that excludes serviceKey to prevent key exposure in logs."""
    safe = {k: v for k, v in params.items() if k != "serviceKey"}
    return endpoint + "|" + "&".join(f"{k}={v}" for k, v in sorted(safe.items()))


def cache_get(key: str) -> Optional[dict]:
    entry = _CACHE.get(key)
    if entry:
        value, ts = entry
        ttl = _TTL_LONG if "ldongCode" in key else _TTL_SHORT
        if time.monotonic() - ts < ttl:
            return value
    return None


def cache_set(key: str, value: dict) -> None:
    _CACHE[key] = (value, time.monotonic())


def get_fetch_lock(key: str) -> asyncio.Lock:
    if key not in _FETCH_LOCKS:
        _FETCH_LOCKS[key] = asyncio.Lock()
    return _FETCH_LOCKS[key]
