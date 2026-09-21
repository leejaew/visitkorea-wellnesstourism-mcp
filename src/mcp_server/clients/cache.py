_TTL_SHORT_SECONDS = 300
_TTL_LONG_SECONDS = 3600


def cache_key(endpoint: str, params: dict) -> str:
    """Build a deterministic key without credentials."""
    safe = {key: value for key, value in params.items() if key != "serviceKey"}
    query = "&".join(f"{key}={value}" for key, value in sorted(safe.items()))
    return f"{endpoint}|{query}"


def cache_ttl(key: str) -> int:
    return (
        _TTL_LONG_SECONDS
        if key.startswith("ldongCode|")
        else _TTL_SHORT_SECONDS
    )