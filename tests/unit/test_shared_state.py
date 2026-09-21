import asyncio
import unittest
from unittest.mock import patch

from mcp_server.clients.shared_state import PostgresSharedState


class _Connection:
    async def fetchrow(self, query):
        return {"cache_table": None, "rate_table": None}


class _Acquire:
    async def __aenter__(self):
        return _Connection()

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _Pool:
    def __init__(self) -> None:
        self.closed = False

    def acquire(self, timeout=None):
        return _Acquire()

    async def close(self) -> None:
        self.closed = True


class SharedStateFailureTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_schema_closes_pool_without_hanging(self) -> None:
        pool = _Pool()

        async def create_pool(*args, **kwargs):
            return pool

        state = PostgresSharedState("postgresql://test")
        with patch(
            "mcp_server.clients.shared_state.asyncpg.create_pool",
            create_pool,
        ):
            with self.assertRaisesRegex(RuntimeError, "schema is missing"):
                await asyncio.wait_for(state.open(), timeout=1)

        self.assertTrue(pool.closed)