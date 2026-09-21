import os
from dataclasses import dataclass

import httpx

BASE_URL = "https://apis.data.go.kr/B551011/WellnessTursmService"

TIMEOUT = httpx.Timeout(
    connect=10.0,
    read=25.0,
    write=5.0,
    pool=5.0,
)

_LIMITS = httpx.Limits(
    max_connections=10,
    max_keepalive_connections=5,
    keepalive_expiry=30,
)


def _csv_env(name: str) -> tuple[str, ...]:
    return tuple(value.strip() for value in os.getenv(name, "").split(",") if value.strip())


def transport_security_policy() -> tuple[tuple[str, ...], tuple[str, ...]]:
    hosts = set(_csv_env("WELLNESS_ALLOWED_HOSTS"))
    hosts.update(_csv_env("REPLIT_DOMAINS"))
    dev_domain = os.getenv("REPLIT_DEV_DOMAIN", "").strip()
    if dev_domain:
        hosts.add(dev_domain)
    hosts.update({"localhost", "localhost:*", "127.0.0.1", "127.0.0.1:*"})

    origins = set(_csv_env("WELLNESS_ALLOWED_ORIGINS"))
    origins.update(f"https://{host}" for host in hosts if "*" not in host)
    origins.update({"http://localhost", "http://127.0.0.1"})
    return tuple(sorted(hosts)), tuple(sorted(origins))


@dataclass(frozen=True)
class Settings:
    api_key: str
    port: int
    allowed_hosts: tuple[str, ...]
    allowed_origins: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "Settings":
        api_key = os.getenv("WELLNESS_API_KEY_ENCODING", "").strip()
        if not api_key:
            raise RuntimeError(
                "WELLNESS_API_KEY_ENCODING is required. "
                "Obtain a key from https://www.data.go.kr/data/15144030/openapi.do."
            )

        try:
            port = int(os.getenv("PORT", "8080"))
        except ValueError as exc:
            raise RuntimeError("PORT must be an integer.") from exc
        if not 1 <= port <= 65535:
            raise RuntimeError("PORT must be between 1 and 65535.")

        hosts, origins = transport_security_policy()

        return cls(
            api_key=api_key,
            port=port,
            allowed_hosts=hosts,
            allowed_origins=origins,
        )


def create_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=TIMEOUT,
        limits=_LIMITS,
        follow_redirects=False,
        headers={"User-Agent": "VisitKorea-Wellness-MCP/1.0"},
    )
