import inspect
from typing import Any

from app.tools import kite
from app.tools.calculate_signal import calculate_signal
from app.tools.crosses_above import crosses_above
from app.tools.crosses_below import crosses_below
from app.tools.ema import ema
from app.tools.generate_link import generate_link
from app.tools.market_history import market_history
from app.tools.rsi import rsi
from app.tools.sma import sma
from app.tools.screener_fundamentals import screener_fundamentals
from app.tools.quality_growth_value import quality_growth_value
from app.tools.portfolio_exposure import portfolio_exposure
from app.tools.vwap import vwap

CUSTOM_TOOLS = {
    "calculate_signal": calculate_signal,
    "sma": sma,
    "indicator.ema": ema,
    "indicator.rsi": rsi,
    "condition.crosses_above": crosses_above,
    "condition.crosses_below": crosses_below,
    "indicator.vwap": vwap,
    "link.generate": generate_link,
    "fundamentals.screener": screener_fundamentals,
    "analysis.quality_growth_value": quality_growth_value,
}
ZERODHA_OPERATIONS = {"market.history": "get_historical_data"}


async def run_tool(
    tool_type: str,
    tool_name: str,
    arguments: dict[str, Any],
    kite_tools: list | None = None,
) -> Any:
    if tool_type == "custom":
        tool = CUSTOM_TOOLS.get(tool_name)
        if tool is None:
            raise RuntimeError(f"Custom tool is unavailable: {tool_name}")
        result = tool(arguments)
        return await result if inspect.isawaitable(result) else result
    if tool_type in {"zerodha", "zerodha_mcp"}:
        operation, tool_name = tool_name, ZERODHA_OPERATIONS.get(tool_name, tool_name)
        if kite_tools is not None:
            return (
                await market_history(arguments, kite_tools)
                if operation == "market.history"
                else await portfolio_exposure(arguments, kite_tools)
                if operation == "portfolio.exposure"
                else await kite.call_kite_tool(kite_tools, tool_name, arguments)
            )
        async with kite.kite_session() as tools:
            return (
                await market_history(arguments, tools)
                if operation == "market.history"
                else await portfolio_exposure(arguments, tools)
                if operation == "portfolio.exposure"
                else await kite.call_kite_tool(tools, tool_name, arguments)
            )
    raise ValueError(f"Unsupported tool type: {tool_type}")
