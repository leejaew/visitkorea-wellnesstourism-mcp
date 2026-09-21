import asyncio
import copy
import time
from collections import OrderedDict
from typing import Optional

_TTL_SHORT = 300.0
_TTL_LONG = 3600.0
_MAX_ENTRIES = 512

_CACHE: OrderedDict[str, tuple[dict, float, float]] = OrderedDict()
_FETCH_LOCKS: dict[str, asyncio.Lock] = {}


def cache_key(endpoint: str, params: dict) -> str:
    safe = {k: v for k, v in params.items() if k != "serviceKey"}
    return endpoint + "|" + "&".join(f"{k}={v}" for k, v in sorted(safe.items()))


def cache_get(key: str) -> Optional[dict]:
    entry = _CACHE.get(key)
    if entry:
        value, ts, ttl = entry
        if time.monotonic() - ts < ttl:
            _CACHE.move_to_end(key)
            return copy.deepcopy(value)
        _CACHE.pop(key, None)
        _FETCH_LOCKS.pop(key, None)
    return None


def cache_set(key: str, value: dict, *, ttl: Optional[float] = None) -> None:
    effective_ttl = ttl if ttl is not None else (
        _TTL_LONG if key.startswith("ldongCode|") else _TTL_SHORT
    )
    _CACHE[key] = (copy.deepcopy(value), time.monotonic(), effective_ttl)
    _CACHE.move_to_end(key)
    while len(_CACHE) > _MAX_ENTRIES:
        evicted_key, _ = _CACHE.popitem(last=False)
        _FETCH_LOCKS.pop(evicted_key, None)


def get_fetch_lock(key: str) -> asyncio.Lock:
    if key not in _FETCH_LOCKS:
        _FETCH_LOCKS[key] = asyncio.Lock()
    return _FETCH_LOCKS[key]


def clear_cache() -> None:
    _CACHE.clear()
    _FETCH_LOCKS.clear()
