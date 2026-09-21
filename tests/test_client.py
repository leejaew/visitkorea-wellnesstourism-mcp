import unittest

import httpx

from api.cache import clear_cache
from api.client import WellnessClient
from api.parser import WellnessAPIError


SUCCESS_BODY = (
    '{"response":{"header":{"resultCode":"0000","resultMsg":"OK"},'
    '"body":{"items":{"item":{"contentId":"1","title":"Test"}},'
    '"numOfRows":10,"pageNo":1,"totalCount":1}}}'
)


class ClientTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        clear_cache()

    async def asyncTearDown(self) -> None:
        clear_cache()

    async def test_valid_response_is_normalized(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.host, "apis.data.go.kr")
            self.assertIn("serviceKey=encoded-key", str(request.url))
            return httpx.Response(200, text=SUCCESS_BODY)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as http_client:
            client = WellnessClient("encoded-key", http_client)
            result = await client.get_wellness_common_info("1")

        self.assertEqual(result["totalCount"], 1)
        self.assertEqual(result["items"][0]["title"], "Test")

    async def test_timeout_is_mapped_to_stable_error(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("internal timeout detail", request=request)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as http_client:
            client = WellnessClient("encoded-key", http_client)
            with self.assertRaises(WellnessAPIError) as raised:
                await client.get_wellness_common_info("2")

        self.assertEqual(raised.exception.code, "TIMEOUT")
        self.assertNotIn("internal timeout detail", raised.exception.message)

    async def test_invalid_inputs_do_not_reach_upstream(self) -> None:
        calls = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(200, text=SUCCESS_BODY)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as http_client:
            client = WellnessClient("encoded-key", http_client)
            with self.assertRaises(ValueError):
                await client.search_wellness_by_location(
                    map_x=float("nan"),
                    map_y=37.5,
                    radius=1000,
                )

        self.assertEqual(calls, 0)