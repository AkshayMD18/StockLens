from typing import Any

from app.tools import kite


def _records(value: Any, symbol: str) -> list[dict]:
    if isinstance(value, list):
        return [record for item in value for record in _records(item, symbol)]
    if not isinstance(value, dict):
        return []
    if value.get("tradingsymbol", "").upper() == symbol:
        return [value]
    return [record for item in value.values() for record in _records(item, symbol)]


async def portfolio_exposure(arguments: dict[str, Any], tools: list) -> dict:
    symbol = arguments.get("symbol", "").upper()
    try:
        holdings = await kite.call_kite_tool(tools, "get_holdings", {})
        positions = await kite.call_kite_tool(tools, "get_positions", {})
    except Exception as error:
        return {"has_position": False, "status": "unavailable", "error": str(error)}
    net_positions = positions.get("net", positions) if isinstance(positions, dict) else positions
    records = [*_records(holdings, symbol), *_records(net_positions, symbol)]
    return {
        "has_position": any(record.get("quantity", 0) != 0 for record in records),
        "status": "available",
        "error": None,
    }
