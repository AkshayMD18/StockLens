import json
import logging
from datetime import date, timedelta
from typing import Any

from app.mcp.kite import call_kite_tool, session

logger = logging.getLogger("stocklens.strategy.tools")


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

    if period <= 0:
        raise ValueError("Period must be positive")

    if len(values) < period:
        raise ValueError(f"Need at least {period} values")

    sma_values: list[float | None] = [None] * (period - 1)

    for i in range(period - 1, len(values)):
        window = values[i - period + 1 : i + 1]
        sma_values.append(sum(window) / period)

    return {
        "values": sma_values,
        "value": sma_values[-1],
    }


def ema(data: dict) -> dict:
    values = data["values"]
    period = data["period"]

    if period <= 0:
        raise ValueError("Period must be positive")

    if len(values) < period:
        raise ValueError(f"Need at least {period} values")

    alpha = 2 / (period + 1)

    ema_values: list[float | None] = [None] * (period - 1)

    # Seed EMA using SMA of the first `period` values
    initial_ema = sum(values[:period]) / period
    ema_values.append(initial_ema)

    previous_ema = initial_ema

    for value in values[period:]:
        current_ema = value * alpha + previous_ema * (1 - alpha)

        ema_values.append(current_ema)
        previous_ema = current_ema

    return {
        "values": ema_values,
        "value": ema_values[-1],
    }


def _crosses(data: dict, direction: str) -> dict:
    series_a = data["series_a"]
    series_b = data["series_b"]

    if len(series_a) != len(series_b):
        raise ValueError("Series must have equal lengths")

    if len(series_a) < 2:
        raise ValueError("Series must contain at least two values")

    previous_a, latest_a = series_a[-2:]
    previous_b, latest_b = series_b[-2:]

    if any(
        value is None
        for value in [
            previous_a,
            latest_a,
            previous_b,
            latest_b,
        ]
    ):
        return {"value": False}

    if direction == "above":
        crossed = previous_a <= previous_b and latest_a > latest_b

    elif direction == "below":
        crossed = previous_a >= previous_b and latest_a < latest_b

    else:
        raise ValueError(f"Invalid crossover direction: {direction}")

    return {
        "value": crossed,
    }


def crosses_above(data: dict) -> dict:
    return _crosses(data, "above")


def crosses_below(data: dict) -> dict:
    return _crosses(data, "below")


CUSTOM_TOOLS = {
    "calculate_signal": calculate_signal,
    "sma": sma,
    "indicator.ema": ema,
    "condition.crosses_above": crosses_above,
    "condition.crosses_below": crosses_below,
}
ZERODHA_OPERATIONS = {"market.history": "get_historical_data"}


def _history_result(result: Any) -> Any:
    candles = _find_candles(result)
    if candles:
        history: dict[str, Any] = {
            field: [candle[field] for candle in candles]
            for field in ("open", "high", "low", "close", "volume")
            if all(field in candle for candle in candles)
        }
        history["latest"] = candles[-1]
        return history
    detail = _response_text(result)
    message = "Kite history response has no candle close series"
    logger.error("kite_history_invalid_response response=%r", result)
    raise ValueError(f"{message}: {detail[:500]}" if detail else message)


def _response_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        text = value.get("text")
        if isinstance(text, str):
            return text
        return " ".join(filter(None, (_response_text(item) for item in value.values())))
    if isinstance(value, list):
        return " ".join(filter(None, (_response_text(item) for item in value)))
    return ""


def _find_candles(value: Any) -> list[dict] | None:
    if (
        isinstance(value, list)
        and value
        and all(isinstance(item, list) and len(item) >= 6 for item in value)
    ):
        return [
            {
                "open": item[1],
                "high": item[2],
                "low": item[3],
                "close": item[4],
                "volume": item[5],
            }
            for item in value
        ]
    if (
        isinstance(value, list)
        and value
        and all(isinstance(item, dict) and "close" in item for item in value)
    ):
        return value
    if isinstance(value, list):
        for item in value:
            candles = _find_candles(item)
            if candles is not None:
                return candles
    if isinstance(value, dict):
        for item in value.values():
            candles = _find_candles(item)
            if candles is not None:
                return candles
    if isinstance(value, str):
        try:
            return _find_candles(json.loads(value))
        except json.JSONDecodeError:
            return None
    return None


def _find_instrument_token(value: Any, symbol: str) -> str | None:
    if isinstance(value, str):
        try:
            return _find_instrument_token(json.loads(value), symbol)
        except json.JSONDecodeError:
            return None
    if isinstance(value, dict):
        if (
            str(value.get("tradingsymbol", value.get("symbol", ""))).upper()
            == symbol.upper()
            and value.get("instrument_token") is not None
            and value.get("exchange", "NSE") == "NSE"
        ):
            return str(value["instrument_token"])
        for item in value.values():
            token = _find_instrument_token(item, symbol)
            if token:
                return token
    if isinstance(value, list):
        for item in value:
            token = _find_instrument_token(item, symbol)
            if token:
                return token
    return None


def _kite_datetime(value: Any, end_of_day: bool) -> str:
    value = str(value)
    return (
        value if " " in value else f"{value} {'23:59:59' if end_of_day else '00:00:00'}"
    )


async def _market_history(arguments: dict[str, Any], tools: list) -> dict:
    symbol = arguments.get("symbol")
    if not isinstance(symbol, str) or not symbol:
        raise ValueError("market.history requires a non-empty symbol")
    logger.info("kite_history_search symbol=%s exchange=NSE", symbol)
    instruments = await call_kite_tool(
        tools, "search_instruments", {"query": symbol, "exchange": "NSE"}
    )
    token = _find_instrument_token(instruments, symbol)
    if token is None:
        raise ValueError(f"No NSE instrument token found for symbol: {symbol}")
    today = date.today()
    from_date = arguments.get("from_date") or (today - timedelta(days=100)).isoformat()
    to_date = arguments.get("to_date") or today.isoformat()
    historical_arguments = {
        "instrument_token": int(token),
        "from_date": _kite_datetime(from_date, False),
        "to_date": _kite_datetime(to_date, True),
        "interval": arguments.get("interval", "day"),
    }
    logger.info(
        "kite_history_request symbol=%s arguments=%s", symbol, historical_arguments
    )
    result = await call_kite_tool(
        tools,
        "get_historical_data",
        historical_arguments,
    )
    return _history_result(result)


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

        return tool(arguments)

    if tool_type in {"zerodha", "zerodha_mcp"}:
        strategy_operation = tool_name
        tool_name = ZERODHA_OPERATIONS.get(tool_name, tool_name)
        if kite_tools is not None:
            if strategy_operation == "market.history":
                return await _market_history(arguments, kite_tools)
            result = await call_kite_tool(kite_tools, tool_name, arguments)
        else:
            async with session() as tools:
                if strategy_operation == "market.history":
                    return await _market_history(arguments, tools)
                result = await call_kite_tool(tools, tool_name, arguments)
        return result

    raise ValueError(f"Unsupported tool type: {tool_type}")
