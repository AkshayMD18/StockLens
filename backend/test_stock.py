import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core import stock


class PatternsRadarTest(unittest.IsolatedAsyncioTestCase):
    async def test_screen_stocks_posts_scan_payload(self):
        response = MagicMock()
        response.json.return_value = {"ok": True, "rows": []}
        client = MagicMock()
        client.post = AsyncMock(return_value=response)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        with (
            patch.object(stock.httpx, "AsyncClient", return_value=client),
        ):
            result = await stock.screen_stocks("rsi_14 > 70", 500, 20)

        self.assertEqual(result, {"ok": True, "rows": []})
        client.post.assert_awaited_once_with(
            stock.SCREENER_URL,
            json={"source": "rsi_14 > 70", "universe": 500, "limit": 20},
        )

    async def test_screen_stocks_rejects_invalid_arguments(self):
        with self.assertRaises(ValueError):
            await stock.screen_stocks("", 500, 20)
        with self.assertRaises(ValueError):
            await stock.screen_stocks("close > ema(21)", 50, 20)
        with self.assertRaises(ValueError):
            await stock.screen_stocks("close > ema(21)", 500, 0)


if __name__ == "__main__":
    unittest.main()
