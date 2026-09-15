import logging

from langchain.messages import AIMessageChunk

logger = logging.getLogger("stocklens.cli")


async def stream_reply(agent, messages: list[dict[str, str]]) -> str:
    response: list[str] = []

    async for chunk in agent.astream(
        {"messages": messages}, stream_mode=["messages", "updates"], version="v2"
    ):
        if chunk["type"] == "messages":
            token, _metadata = chunk["data"]
            if isinstance(token, AIMessageChunk) and token.text:
                print(token.text, end="", flush=True)
                response.append(token.text)
        elif chunk["type"] == "updates":
            for node, update in chunk["data"].items():
                for message in update.get("messages", []):
                    if getattr(message, "tool_calls", None):
                        logger.info("tool_call node=%s calls=%s", node, message.tool_calls)
                    if node == "tools":
                        logger.info("tool_response content=%s", message.content)

    print()
    return "".join(response)
