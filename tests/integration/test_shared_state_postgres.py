import asyncio
import os
import unittest
import uuid

from mcp_server.clients.shared_state import PostgresSharedState


@unittest.skipUnless(os.getenv("DATABASE_URL"), "DATABASE_URL is not available")
class PostgresSharedStateTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        database_url = os.environ["DATABASE_URL"]
        self.first = PostgresSharedState(database_url)
        self.second = PostgresSharedState(database_url)
        await self.first.open()
        await self.second.open()
        self.prefix = f"integration|{uuid.uuid4()}"

    async def asyncTearDown(self) -> None:
        await self.first.close()
        await self.second.close()

    async def test_cache_is_visible_across_independent_pools(self) -> None:
        key = f"{self.prefix}|cache"
        await self.first.cache_set(key, {"shared": True}, 30)
        self.assertEqual(
            await self.second.cache_get(key), {"shared": True}
        )

    async def test_rate_counter_is_atomic_across_pools(self) -> None:
        client_id = f"{self.prefix}|rate"
        counts = await asyncio.gather(
            *[
                (self.first if index % 2 else self.second).increment_rate_limit(
                    client_id, 60
                )
                for index in range(20)
            ]
        )
        self.assertEqual(sorted(counts), list(range(1, 21)))

    async def test_advisory_lock_does_not_starve_pool(self) -> None:
        key = f"{self.prefix}|lock"

        async def increment(state: PostgresSharedState) -> None:
            async with state.fetch_lock(key) as lease:
                current = await lease.cache_get(key) or {"count": 0}
                await asyncio.sleep(0.01)
                await lease.cache_set(
                    key, {"count": current["count"] + 1}, 30
                )

        await asyncio.wait_for(
            asyncio.gather(
                *[
                    increment(self.first if index % 2 else self.second)
                    for index in range(12)
                ]
            ),
            timeout=10,
        )
        self.assertEqual(
            await self.first.cache_get(key), {"count": 12}
        )

    async def test_rate_limit_fails_within_bound_when_pool_is_exhausted(
        self,
    ) -> None:
        state = PostgresSharedState(
            os.environ["DATABASE_URL"], pool_acquire_timeout=0.05
        )
        await state.open()
        pool = state._require_pool()
        connections = [
            await pool.acquire() for _ in range(pool.get_max_size())
        ]
        try:
            with self.assertRaises((TimeoutError, asyncio.TimeoutError)):
                await state.increment_rate_limit(
                    f"{self.prefix}|exhausted", 60
                )
        finally:
            for connection in connections:
                await pool.release(connection)
            await state.close()