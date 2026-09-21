import unittest

from mcp_server.clients.cache import cache_key
from mcp_server.clients.shared_state import MemorySharedState


class CacheTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.state = MemorySharedState()

    async def asyncTearDown(self) -> None:
        await self.state.close()

    def test_cache_key_excludes_service_key(self) -> None:
        key = cache_key(
            "detailCommon", {"serviceKey": "secret", "contentId": "1"}
        )
        self.assertNotIn("secret", key)
        self.assertEqual(key, "detailCommon|contentId=1")

    async def test_cached_values_are_isolated_from_mutation(self) -> None:
        await self.state.cache_set(
            "key", {"items": [{"title": "original"}]}, 60
        )
        first = await self.state.cache_get("key")
        assert first is not None
        first["items"][0]["title"] = "changed"
        second = await self.state.cache_get("key")
        assert second is not None
        self.assertEqual(second["items"][0]["title"], "original")

    async def test_expired_entries_are_removed(self) -> None:
        await self.state.cache_set("key", {"items": []}, -1)
        self.assertIsNone(await self.state.cache_get("key"))

    async def test_state_is_shared_by_multiple_consumers(self) -> None:
        first_consumer = self.state
        second_consumer = self.state
        await first_consumer.cache_set("shared", {"value": 1}, 60)
        self.assertEqual(
            await second_consumer.cache_get("shared"), {"value": 1}
        )