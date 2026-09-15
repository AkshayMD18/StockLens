import unittest
from unittest.mock import AsyncMock

from langchain.messages import AIMessageChunk

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

    async def test_kite_login_calls_login_tool_without_agent(self):
        login_tool = type(
            "LoginTool",
            (),
            {
                "name": "login",
                "ainvoke": AsyncMock(return_value="https://kite.trade/login"),
            },
        )()

        self.assertEqual(await kite_login([login_tool]), "https://kite.trade/login")
        login_tool.ainvoke.assert_awaited_once_with({})

    async def test_kite_status_calls_profile_tool_without_agent(self):
        profile_tool = type(
            "ProfileTool",
            (),
            {
                "name": "get_profile",
                "ainvoke": AsyncMock(return_value={"user_name": "Ava"}),
            },
        )()

        self.assertEqual(await kite_status([profile_tool]), {"user_name": "Ava"})
        profile_tool.ainvoke.assert_awaited_once_with({})


if __name__ == "__main__":
    unittest.main()
