import unittest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

from app.mcp.kite import session


class KiteMcpTest(unittest.IsolatedAsyncioTestCase):
    async def test_loads_tools_from_one_active_kite_session(self):
        @asynccontextmanager
        async def client_session():
            yield "kite-session"

        with (
            patch("app.mcp.kite.MultiServerMCPClient") as client_class,
            patch("app.mcp.kite.load_mcp_tools", AsyncMock(return_value=["quote"])) as load_tools,
        ):
            client = client_class.return_value
            client.session.return_value = client_session()

            async with session() as tools:
                self.assertEqual(tools, ["quote"])

            client_class.assert_called_once_with(
                {
                    "kite": {
                        "url": "https://mcp.kite.trade/mcp",
                        "transport": "streamable_http",
                        "timeout": 60,
                        "sse_read_timeout": 120,
                        "terminate_on_close": False,
                    }
                }
            )
            client.session.assert_called_once_with("kite")
            load_tools.assert_awaited_once_with("kite-session", server_name="kite")


if __name__ == "__main__":
    unittest.main()
