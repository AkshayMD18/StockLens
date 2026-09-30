import logging
from datetime import date, timedelta
from typing import Any
from app.tools import kite
from app.tools.history_date import history_date
from app.tools.history_result import history_result
from app.tools.kite_datetime import kite_datetime
from app.tools.resolve_instrument import resolve_instrument
logger = logging.getLogger("stocklens.strategy.tools")


async def market_history(arguments: dict[str, Any], tools: list) -> dict:
    symbol = arguments.get("symbol")
    if not isinstance(symbol, str) or not symbol: raise ValueError("market.history requires a non-empty symbol")
    logger.info("kite_history_search symbol=%s exchange=NSE", symbol)
    token = arguments.get("instrument_token")
    if token is None: token = (await resolve_instrument(arguments["symbol"], tools))["instrument_token"]
    today, lookback_days = date.today(), arguments.get("lookback_days", 100)
    if not isinstance(lookback_days, int) or isinstance(lookback_days, bool) or lookback_days <= 0: raise ValueError("market.history lookback_days must be a positive integer")
    from_date = history_date(arguments.get("from_date") or (today - timedelta(days=lookback_days)).isoformat(), today)
    to_date = history_date(arguments.get("to_date") or today.isoformat(), today)
    request = {"instrument_token": int(token), "from_date": kite_datetime(from_date, False), "to_date": kite_datetime(to_date, True), "interval": arguments.get("interval", "day")}
    logger.info("kite_history_request symbol=%s arguments=%s", symbol, request)
    return history_result(await kite.call_kite_tool(tools, "get_historical_data", request))
