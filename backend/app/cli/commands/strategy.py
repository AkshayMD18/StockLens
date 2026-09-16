from functools import partial

from app.db.database import SessionLocal
from app.db.models import Strategy
from app.strategy.strategy_executor import StrategyError, StrategyExecutor
from app.strategy.tools import run_tool


async def execute(strategy_id: str, symbol: str, kite_tools: list | None = None) -> dict:
    try:
        parsed_strategy_id = int(strategy_id)
    except (TypeError, ValueError) as error:
        raise ValueError("Strategy ID must be an integer") from error
    if parsed_strategy_id <= 0:
        raise ValueError("Strategy ID must be a positive integer")
    if not symbol.strip():
        raise ValueError("Stock symbol is required")

    db = SessionLocal()
    try:
        record = db.get(Strategy, parsed_strategy_id)
    finally:
        db.close()
    if record is None:
        raise ValueError(f"Strategy not found: {parsed_strategy_id}")

    try:
        tool_runner = partial(run_tool, kite_tools=kite_tools)
        return await StrategyExecutor(tool_runner=tool_runner).execute(
            record.strategy, {"symbol": symbol.upper()}, include_state=True
        )
    except StrategyError as error:
        raise ValueError(f"Strategy {parsed_strategy_id} failed: {error}") from error
