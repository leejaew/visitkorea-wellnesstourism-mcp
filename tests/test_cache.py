import unittest

from api.cache import cache_get, cache_key, cache_set, clear_cache


class CacheTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_cache()

    def tearDown(self) -> None:
        clear_cache()

    def test_cache_key_excludes_service_key(self) -> None:
        key = cache_key("detailCommon", {"serviceKey": "secret", "contentId": "1"})
        self.assertNotIn("secret", key)
        self.assertEqual(key, "detailCommon|contentId=1")

    def test_cached_values_are_isolated_from_mutation(self) -> None:
        cache_set("key", {"items": [{"title": "original"}]})
        first = cache_get("key")
        assert first is not None
        first["items"][0]["title"] = "changed"
        second = cache_get("key")
        assert second is not None
        self.assertEqual(second["items"][0]["title"], "original")

    def test_expired_entries_are_removed(self) -> None:
        cache_set("key", {"items": []}, ttl=-1)
        self.assertIsNone(cache_get("key"))