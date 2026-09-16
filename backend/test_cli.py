import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from langchain.messages import AIMessageChunk
from langchain_core.messages import HumanMessage
from rich.console import Console

from app.agents.research import relevant_tools
import app.cli.query as query
import app.cli.main as cli_main
from app.cli import kite_login, kite_status, stream_reply


class FakeAgent:
    async def astream(self, _state, stream_mode, version):
        if stream_mode != ["messages", "updates"] or version != "v2":
            raise AssertionError("expected v2 message and update streaming")
        yield {"type": "messages", "data": (AIMessageChunk(content="Hello"), {})}
        yield {"type": "messages", "data": (AIMessageChunk(content=" there"), {})}


class CliTest(unittest.IsolatedAsyncioTestCase):
    async def test_stream_reply_collects_model_text(self):
        response = await stream_reply(FakeAgent(), [{"role": "user", "content": "Hi"}])

        self.assertEqual(response, "Hello there")

    async def test_stream_reply_preserves_markdown_table_text(self):
        class TableAgent:
            async def astream(self, *_args, **_kwargs):
                yield {"type": "messages", "data": (AIMessageChunk(content="| Name | Price |\n"), {})}
                yield {"type": "messages", "data": (AIMessageChunk(content="| --- | ---: |\n| ACME | 42 |"), {})}

        console = Console(record=True, force_terminal=True)
        with patch.object(query, "console", console):
            response = await stream_reply(TableAgent(), [])

        self.assertEqual(response, "| Name | Price |\n| --- | ---: |\n| ACME | 42 |")
        self.assertIn("Name", console.export_text())

    def test_relevant_tools_filters_and_orders_tools(self):
        names = (
            "get_ltp", "get_ohlc", "get_quotes", "get_historical_data",
            "get_holdings", "get_positions", "get_profile", "get_margins",
            "get_orders", "get_trades",
        )
        tools = {name: SimpleNamespace(name=name) for name in names}

        cases = {
            "Analyse ZYDUSLIFE stock": ["get_ltp", "get_ohlc", "get_quotes", "get_historical_data"],
            "Show my holdings and PnL": ["get_holdings", "get_positions"],
            "Show account margin": ["get_profile", "get_margins"],
            "Show my orders": ["get_orders", "get_trades"],
            "Hello": [],
        }

        for message, expected in cases.items():
            selected = relevant_tools([HumanMessage(content=message)], tools)
            self.assertEqual([tool.name for tool in selected], expected)

    async def test_main_keeps_kite_session_open_while_running(self):
        session_open = False

        @asynccontextmanager
        async def fake_session():
            nonlocal session_open
            session_open = True
            try:
                yield ["kite"]
            finally:
                session_open = False

        async def fake_run(agent, tools):
            self.assertTrue(session_open)
            self.assertEqual((agent, tools), ("agent", ["kite"]))

        with (
            patch.object(cli_main, "kite_session", fake_session),
            patch.object(cli_main, "create_research_agent", AsyncMock(return_value="agent")),
            patch.object(cli_main, "run", fake_run),
        ):
            await cli_main.main()

    async def test_kite_login_calls_login_tool_without_agent(self):
        login_tool = type(
            "LoginTool",
            (),
            {
                "name": "login",
                "ainvoke": AsyncMock(return_value="https://kite.trade/login"),
            },
        )()

        rendered = await kite_login([login_tool])
        self.assertEqual(type(rendered).__name__, "Markdown")
        login_tool.ainvoke.assert_awaited_once_with({})

    async def test_kite_status_calls_profile_tool_without_agent(self):
        profile_tool = type(
            "ProfileTool",
            (),
            {
                "name": "get_profile",
            "ainvoke": AsyncMock(
                return_value=[{"type": "text", "text": '{"user_name":"Ava"}'}]
            ),
            },
        )()

        rendered = await kite_status([profile_tool])
        self.assertEqual(type(rendered).__name__, "Table")
        profile_tool.ainvoke.assert_awaited_once_with({})


if __name__ == "__main__":
    unittest.main()
