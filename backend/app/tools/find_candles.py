import json
from typing import Any


def find_candles(value: Any) -> list[dict] | None:
    if isinstance(value, list) and value and all(isinstance(item, list) and len(item) >= 6 for item in value):
        return [{"open": item[1], "high": item[2], "low": item[3], "close": item[4], "volume": item[5]} for item in value]
    if isinstance(value, list) and value and all(isinstance(item, dict) and "close" in item for item in value): return value
    if isinstance(value, (list, dict)):
        for item in value if isinstance(value, list) else value.values():
            candles = find_candles(item)
            if candles is not None: return candles
    if isinstance(value, str):
        try: return find_candles(json.loads(value))
        except json.JSONDecodeError: return None
    return None
