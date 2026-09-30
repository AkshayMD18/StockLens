from app.tools import kite
from app.tools.find_instrument_token import find_instrument_token


async def resolve_instrument(symbol, kite_tools=None):
    if kite_tools is None:
        async with kite.kite_session() as kite_tools: return await resolve_instrument(symbol, kite_tools)
    symbol = symbol.upper()
    token = find_instrument_token(await kite.call_kite_tool(kite_tools, "search_instruments", {"query": symbol, "exchange": "NSE"}), symbol)
    if token is None: raise ValueError(f"No exact NSE instrument found for {symbol}")
    return {"exchange": "NSE", "tradingsymbol": symbol, "instrument_token": token}
