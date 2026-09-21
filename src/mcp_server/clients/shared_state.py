import asyncio
import copy
import hashlib
import json
import time
from collections import OrderedDict
from contextlib import asynccontextmanager
from typing import AsyncContextManager, AsyncIterator, Protocol

import asyncpg


class CacheLease(Protocol):
    async def cache_get(self, key: str) -> dict | None: ...

    async def cache_set(self, key: str, value: dict, ttl_seconds: int) -> None: ...


class SharedState(CacheLease, Protocol):
    async def open(self) -> None: ...

    async def close(self) -> None: ...

    async def cache_get(self, key: str) -> dict | None: ...

    async def cache_set(self, key: str, value: dict, ttl_seconds: int) -> None: ...

    def fetch_lock(self, key: str) -> AsyncContextManager[CacheLease]: ...

    async def increment_rate_limit(
        self, client_id: str, window_seconds: int
    ) -> int: ...


class PostgresSharedState:
    """Cross-instance cache, stampede lock, and rate counter."""

    def __init__(
        self, database_url: str, pool_acquire_timeout: float = 10
    ) -> None:
        if not database_url:
            raise ValueError("database_url must not be empty.")
        self.database_url = database_url
        self.pool_acquire_timeout = pool_acquire_timeout
        self._pool: asyncpg.Pool | None = None

    async def open(self) -> None:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=5,
                command_timeout=10,
            )
            async with self._pool.acquire(
                timeout=self.pool_acquire_timeout
            ) as connection:
                row = await connection.fetchrow(
                    """
                    SELECT
                        to_regclass('wellness_mcp_cache') AS cache_table,
                        to_regclass('wellness_mcp_rate_limits') AS rate_table
                    """
                )
            schema_ready = (
                row is not None
                and row["cache_table"] is not None
                and row["rate_table"] is not None
            )
            if not schema_ready:
                await self.close()
                raise RuntimeError(
                    "Shared-state database schema is missing. "
                    "Apply docs/shared_state_schema.sql."
                )

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Shared state has not been opened.")
        return self._pool

    async def cache_get(self, key: str) -> dict | None:
        async with self._require_pool().acquire(
            timeout=self.pool_acquire_timeout
        ) as connection:
            return await self._cache_get(connection, key)

    @staticmethod
    async def _cache_get(
        connection: asyncpg.Connection, key: str
    ) -> dict | None:
        row = await connection.fetchrow(
            """
            SELECT payload
            FROM wellness_mcp_cache
            WHERE cache_key = $1 AND expires_at > NOW()
            """,
            key,
        )
        if row is None:
            return None
        payload = row["payload"]
        return json.loads(payload) if isinstance(payload, str) else payload

    async def cache_set(
        self, key: str, value: dict, ttl_seconds: int
    ) -> None:
        async with self._require_pool().acquire(
            timeout=self.pool_acquire_timeout
        ) as connection:
            await self._cache_set(connection, key, value, ttl_seconds)

    @staticmethod
    async def _cache_set(
        connection: asyncpg.Connection,
        key: str,
        value: dict,
        ttl_seconds: int,
    ) -> None:
        await connection.execute(
            """
            WITH cleanup AS (
                DELETE FROM wellness_mcp_cache
                WHERE expires_at <= NOW()
            )
            INSERT INTO wellness_mcp_cache (cache_key, payload, expires_at)
            VALUES ($1, $2::jsonb, NOW() + ($3 * INTERVAL '1 second'))
            ON CONFLICT (cache_key) DO UPDATE
            SET payload = EXCLUDED.payload, expires_at = EXCLUDED.expires_at
            """,
            key,
            json.dumps(value),
            ttl_seconds,
        )

    @asynccontextmanager
    async def fetch_lock(self, key: str) -> AsyncIterator[CacheLease]:
        lock_id = int.from_bytes(
            hashlib.sha256(key.encode()).digest()[:8],
            byteorder="big",
            signed=True,
        )
        pool = self._require_pool()
        async with pool.acquire(
            timeout=self.pool_acquire_timeout
        ) as connection:
            await connection.execute("SELECT pg_advisory_lock($1)", lock_id)
            try:
                yield _PostgresCacheLease(connection)
            finally:
                await connection.execute("SELECT pg_advisory_unlock($1)", lock_id)

    async def increment_rate_limit(
        self, client_id: str, window_seconds: int
    ) -> int:
        window_epoch = int(time.time()) // window_seconds
        async with self._require_pool().acquire(
            timeout=self.pool_acquire_timeout
        ) as connection:
            row = await connection.fetchrow(
                """
                WITH cleanup AS (
                    DELETE FROM wellness_mcp_rate_limits
                    WHERE window_epoch < $3
                )
                INSERT INTO wellness_mcp_rate_limits (
                    client_id, window_epoch, request_count
                )
                VALUES ($1, $2, 1)
                ON CONFLICT (client_id, window_epoch) DO UPDATE
                SET request_count = wellness_mcp_rate_limits.request_count + 1
                RETURNING request_count
                """,
                client_id,
                window_epoch,
                window_epoch - 2,
            )
        return int(row["request_count"])


class _PostgresCacheLease:
    def __init__(self, connection: asyncpg.Connection) -> None:
        self.connection = connection

    async def cache_get(self, key: str) -> dict | None:
        return await PostgresSharedState._cache_get(self.connection, key)

    async def cache_set(
        self, key: str, value: dict, ttl_seconds: int
    ) -> None:
        await PostgresSharedState._cache_set(
            self.connection, key, value, ttl_seconds
        )


class MemorySharedState:
    """Deterministic test implementation of the shared-state contract."""

    def __init__(self, max_entries: int = 512) -> None:
        self.max_entries = max_entries
        self._cache: OrderedDict[str, tuple[dict, float]] = OrderedDict()
        self._locks: dict[str, asyncio.Lock] = {}
        self._rates: dict[tuple[str, int], int] = {}

    async def open(self) -> None:
        return None

    async def close(self) -> None:
        self.clear()

    async def cache_get(self, key: str) -> dict | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at <= time.monotonic():
            self._cache.pop(key, None)
            self._locks.pop(key, None)
            return None
        self._cache.move_to_end(key)
        return copy.deepcopy(value)

    async def cache_set(
        self, key: str, value: dict, ttl_seconds: int
    ) -> None:
        self._cache[key] = (
            copy.deepcopy(value),
            time.monotonic() + ttl_seconds,
        )
        self._cache.move_to_end(key)
        while len(self._cache) > self.max_entries:
            evicted_key, _ = self._cache.popitem(last=False)
            self._locks.pop(evicted_key, None)

    @asynccontextmanager
    async def fetch_lock(self, key: str) -> AsyncIterator[CacheLease]:
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            yield self

    async def increment_rate_limit(
        self, client_id: str, window_seconds: int
    ) -> int:
        window_epoch = int(time.time()) // window_seconds
        key = (client_id, window_epoch)
        self._rates[key] = self._rates.get(key, 0) + 1
        stale_before = window_epoch - 2
        self._rates = {
            stored_key: count
            for stored_key, count in self._rates.items()
            if stored_key[1] >= stale_before
        }
        return self._rates[key]

    def clear(self) -> None:
        self._cache.clear()
        self._locks.clear()
        self._rates.clear()