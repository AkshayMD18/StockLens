"""Run a direct Kite historical-data check for one NSE symbol."""

import argparse
import asyncio
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.mcp.kite import call_kite_tool, session
from app.strategy.tools import _find_instrument_token, _history_result, _kite_datetime


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", nargs="?", default="RELIANCE")
    parser.add_argument("--from-date")
    parser.add_argument("--to-date", default=date.today().isoformat())
    parser.add_argument(
        "--login", action="store_true", help="Log in through this MCP session first"
    )
    args = parser.parse_args()

    from_date = args.from_date or (date.today() - timedelta(days=200)).isoformat()
    async with session() as tools:
        history_tool = next(
            tool for tool in tools if tool.name == "get_historical_data"
        )
        print("Kite history schema:", json.dumps(history_tool.args, default=str))
        if args.login:
            print("Kite login:", await call_kite_tool(tools, "login", {}))
            await asyncio.to_thread(
                input,
                "Open the login URL above, finish Zerodha login, then press Enter here...",
            )

        instruments = await call_kite_tool(
            tools, "search_instruments", {"query": args.symbol, "exchange": "NSE"}
        )
        token = _find_instrument_token(instruments, args.symbol)
        if token is None:
            raise RuntimeError(f"No NSE instrument token found for {args.symbol}")

        request = {
            "instrument_token": int(token),
            "from_date": _kite_datetime(from_date, False),
            "to_date": _kite_datetime(args.to_date, True),
            "interval": "day",
        }
        print("Kite request:", json.dumps(request))
        response = await call_kite_tool(tools, "get_historical_data", request)
        print("Kite response:", json.dumps(response, default=str)[:2000])
        history = _history_result(response)
        print(
            f"PASS: {len(history['close'])} daily close candles; latest={history['close'][-1]}"
        )


if __name__ == "__main__":
    asyncio.run(main())
