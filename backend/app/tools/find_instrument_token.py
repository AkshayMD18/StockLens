import json
from typing import Any


def find_instrument_token(value: Any, symbol: str) -> str | None:
    if isinstance(value, str):
        try: return find_instrument_token(json.loads(value), symbol)
        except json.JSONDecodeError: return None
    if isinstance(value, dict):
        if str(value.get("tradingsymbol", value.get("symbol", ""))).upper() == symbol.upper() and value.get("instrument_token") is not None and value.get("exchange", "NSE") == "NSE": return str(value["instrument_token"])
        for item in value.values():
            token = find_instrument_token(item, symbol)
            if token: return token
    if isinstance(value, list):
        for item in value:
            token = find_instrument_token(item, symbol)
            if token: return token
    return None
