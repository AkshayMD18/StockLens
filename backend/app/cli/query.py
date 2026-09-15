import logging

from langchain.messages import AIMessageChunk
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

logger = logging.getLogger("stocklens.cli")
console = Console()


async def stream_reply(agent, messages: list[dict[str, str]]) -> str:
    response: list[str] = []

    with Live(Markdown(""), console=console, refresh_per_second=12) as live:
        async for chunk in agent.astream(
            {"messages": messages}, stream_mode=["messages", "updates"], version="v2"
        ):
            if chunk["type"] == "messages":
                token, _metadata = chunk["data"]
                if isinstance(token, AIMessageChunk) and token.text:
                    response.append(token.text)
                    live.update(Markdown("".join(response)))
            elif chunk["type"] == "updates":
                for node, update in chunk["data"].items():
                    for message in update.get("messages", []):
                        if getattr(message, "tool_calls", None):
                            logger.info("tool_call node=%s calls=%s", node, message.tool_calls)
                        if node == "tools":
                            logger.info("tool_response content=%s", message.content)

    return "".join(response)
