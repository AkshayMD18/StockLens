from typing import Any

from app.mcp.kite import call_kite_tool, session


def calculate_signal(data: dict) -> dict:
    prices = data["prices"]

    if len(prices) < 2:
        raise ValueError("At least two prices are required")

    signal = "buy" if prices[-1] > prices[-2] else "sell"

    return {
        "signal": signal,
        "latest_price": prices[-1],
    }


def sma(data: dict) -> dict:
    values = data["values"]
    period = data["period"]

    if len(values) < period:
        raise ValueError(f"Need at least {period} values")

    return {
        "sma": sum(values[-period:]) / period,
    }


CUSTOM_TOOLS = {
    "calculate_signal": calculate_signal,
    "sma": sma,
}


async def run_tool(
    tool_type: str,
    tool_name: str,
    arguments: dict[str, Any],
) -> Any:
    if tool_type == "custom":
        tool = CUSTOM_TOOLS.get(tool_name)

        if tool is None:
            raise RuntimeError(f"Custom tool is unavailable: {tool_name}")

        return tool(arguments)

    if tool_type == "zerodha_mcp":
        async with session() as tools:
            return await call_kite_tool(tools, tool_name, arguments)

    raise ValueError(f"Unsupported tool type: {tool_type}")
