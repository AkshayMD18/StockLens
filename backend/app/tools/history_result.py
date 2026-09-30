import logging
from typing import Any
from app.tools.find_candles import find_candles
from app.tools.response_text import response_text
logger = logging.getLogger("stocklens.strategy.tools")


def history_result(result: Any) -> Any:
    candles = find_candles(result)
    if candles:
        history: dict[str, Any] = {field: [candle[field] for candle in candles] for field in ("open", "high", "low", "close", "volume") if all(field in candle for candle in candles)}
        history["latest"] = candles[-1]
        return history
    detail, message = response_text(result), "Kite history response has no candle close series"
    logger.error("kite_history_invalid_response response=%r", result)
    raise ValueError(f"{message}: {detail[:500]}" if detail else message)
