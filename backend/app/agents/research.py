from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, ModelResponse, wrap_model_call
from langchain_core.messages import HumanMessage

from app.core.groq import groq_model


def relevant_tools(messages, tool_by_name):
    message = next(
        (
            str(item.content).lower()
            for item in reversed(messages)
            if isinstance(item, HumanMessage)
        ),
        "",
    )

    names: list[str] = []

    if any(
        word in message for word in ("stock", "share", "price", "analysis", "quote")
    ):
        names += ["get_ltp", "get_ohlc", "get_quotes", "get_historical_data"]

    if any(word in message for word in ("holding", "portfolio", "position", "pnl")):
        names += ["get_holdings", "get_positions"]

    if any(word in message for word in ("profile", "account", "margin", "fund")):
        names += ["get_profile", "get_margins"]

    if any(word in message for word in ("order", "buy", "sell")):
        names += ["get_orders", "get_trades"]

    return [tool_by_name[name] for name in dict.fromkeys(names) if name in tool_by_name]


async def create_research_agent(tools: list | None = None):
    tools = tools or []
    tool_by_name = {tool.name: tool for tool in tools}

    @wrap_model_call
    async def filter_tools(request: ModelRequest, handler) -> ModelResponse:
        return await handler(
            request.override(tools=relevant_tools(request.messages, tool_by_name))
        )

    prompt = """
    You are StockLens, a conversational stock research assistant.
    Once you have enough information, give the user a concise and useful answer.
    """

    if tools:
        prompt += """
        You have access to Zerodha Kite MCP tools. Use them for market and
        account data when relevant. Call the tool that matches the requested
        data and its documented inputs. Do not call tools unnecessarily.
        """

    return create_agent(
        model=groq_model,
        tools=tools,
        system_prompt=prompt,
        middleware=[filter_tools],
    )
