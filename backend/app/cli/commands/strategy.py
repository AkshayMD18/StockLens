from functools import partial

from rich.table import Table

from app.db.database import SessionLocal
from app.db.models import Strategy
from app.strategy.strategy_executor import StrategyError, StrategyExecutor
from app.strategy.tools import run_tool


async def run_strategy(
    strategy_id: str, symbol: str, kite_tools: list | None = None
) -> dict:
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


async def list_strategies() -> Table:
    db = SessionLocal()
    try:
        strategies = db.query(Strategy).order_by(Strategy.id).all()
    finally:
        db.close()

    table = Table(title="Strategies")
    table.add_column("ID")
    table.add_column("Name")

    for strategy in strategies:
        table.add_row(str(strategy.id), strategy.name)

    return table


async def strategy_details(strategy_id: str) -> str | None:
    db = SessionLocal()
    try:
        strategy = db.get(Strategy, int(strategy_id))
    finally:
        db.close()

    if strategy is None:
        return None

    return (
        f"[bold cyan]ID:[/] {strategy.id}\n"
        f"[bold cyan]Name:[/] {strategy.name}\n"
        f"[bold cyan]Description:[/] {strategy.description}\n"
        f"[bold cyan]Prompt:[/] {strategy.prompt}"
    )
