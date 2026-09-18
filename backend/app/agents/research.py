import json

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, ModelResponse, wrap_model_call
from langchain.tools import tool
from langchain_core.messages import HumanMessage

from app.cli.commands.strategy import execute as run_strategy
from app.core.groq import groq_model
from app.db.database import SessionLocal
from app.db.models import Strategy


def _kite_data(response):
    """Decode the text payload returned by Kite MCP, preserving native values."""
    if isinstance(response, list):
        text = next(
            (
                item.get("text")
                for item in response
                if isinstance(item, dict) and "text" in item
            ),
            None,
        )
        if text is not None:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return response
    return response


def _symbol_records(value, symbol):
    if isinstance(value, list):
        return [record for item in value for record in _symbol_records(item, symbol)]
    if not isinstance(value, dict):
        return []
    if value.get("tradingsymbol", "").upper() == symbol:
        return [value]
    return [
        record for item in value.values() for record in _symbol_records(item, symbol)
    ]


def _position_records(value):
    """Use Kite's net positions; its day positions would duplicate exposure."""
    if isinstance(value, dict) and isinstance(value.get("net"), list):
        return value["net"]
    return value


def _portfolio_status(symbol, holdings, positions, errors):
    holding_records = _symbol_records(holdings, symbol)
    position_records = _symbol_records(_position_records(positions), symbol)
    records = [*holding_records, *position_records]
    exposure = [
        {
            key: record[key]
            for key in ("quantity", "average_price", "last_price", "pnl", "product")
            if key in record
        }
        for record in records
    ]
    return {
        "symbol": symbol,
        "status": "unavailable" if errors else "available",
        "error": "; ".join(errors) if errors else None,
        "has_exposure": None
        if errors
        else any(record.get("quantity", 0) != 0 for record in records),
        "summary": {
            "holding_quantity": sum(
                record.get("quantity", 0) for record in holding_records
            ),
            "net_position_quantity": sum(
                record.get("quantity", 0) for record in position_records
            ),
            "exposure": exposure,
        },
        "holdings": holding_records,
        "positions": position_records,
    }


async def _portfolio_context(tools, symbol):
    results, errors = {}, []
    for name, key in (("get_holdings", "holdings"), ("get_positions", "positions")):
        kite_tool = next((item for item in tools if item.name == name), None)
        if kite_tool is None:
            errors.append(f"Kite tool is unavailable: {name}")
            continue
        try:
            results[key] = _kite_data(await kite_tool.ainvoke({}))
        except Exception as error:
            errors.append(f"{name}: {error}")
    return _portfolio_status(
        symbol, results.get("holdings", []), results.get("positions", []), errors
    )


def relevant_tools(messages, tool_by_name):
    message = next(
        (
            str(item.content).lower()
            for item in reversed(messages)
            if isinstance(item, HumanMessage)
        ),
        "",
    )

    names: list[str] = []

    strategy_request = any(
        word in message
        for word in (
            "strategy",
            "backtest",
            "implement",
            "crossover",
            "ema",
            "sma",
            "signal",
        )
    )
    if strategy_request:
        names += ["execute_strategy"]
    else:
        if any(word in message for word in ("history", "historical", "candle", "year")):
            names += ["search_instruments", "get_historical_data"]
        elif any(
            word in message for word in ("stock", "share", "price", "analysis", "quote")
        ):
            names += ["get_ltp", "get_ohlc", "get_quotes", "get_historical_data"]

    if not strategy_request and any(
        word in message for word in ("holding", "portfolio", "position", "pnl")
    ):
        names += ["get_holdings", "get_positions"]

    if any(word in message for word in ("profile", "account", "margin", "fund")):
        names += ["get_profile", "get_margins"]

    if any(word in message for word in ("order", "buy", "sell")):
        names += ["get_orders", "get_trades"]

    return [tool_by_name[name] for name in dict.fromkeys(names) if name in tool_by_name]


async def create_research_agent(tools: list | None = None):
    tools = tools or []

    @tool
    async def execute_strategy(strategy_name: str, symbol: str) -> dict:
        """Get Zerodha exposure, then run a stored deterministic NSE strategy."""

        symbol = symbol.upper()

        db = SessionLocal()
        try:
            strategy = (
                db.query(Strategy).filter(Strategy.name.ilike(strategy_name)).first()
            )
        finally:
            db.close()

        if strategy is None:
            raise ValueError(f"Strategy not found: {strategy_name}")

        portfolio = await _portfolio_context(tools, symbol)
        execution = await run_strategy(
            str(strategy.id),
            symbol,
            kite_tools=tools,
        )
        return {
            "portfolio": portfolio,
            "decision": execution["result"]["decision"],
            "analysis": execution.get("analysis", {}),
            "prompt": strategy.prompt,
        }

    tools = [*tools, execute_strategy]
    tool_by_name = {tool.name: tool for tool in tools}

    @wrap_model_call
    async def filter_tools(request: ModelRequest, handler) -> ModelResponse:
        return await handler(
            request.override(tools=relevant_tools(request.messages, tool_by_name))
        )

    prompt = """
    You are StockLens, a conversational stock research assistant.

    When the user asks to run, implement, analyze, or backtest a known trading
    strategy on a stock, you MUST call execute_strategy.

    Do not calculate indicators yourself.
    Do not invent strategy results.
    The execute_strategy result is deterministic and authoritative.

    The tool's decision is authoritative: describe only the configured
    strategy signals and never infer alternate rules from indicator values.
    Once the tool returns, summarize its portfolio context, decision, and
    analysis concisely. If portfolio status is unavailable, say so clearly.

    After execute_strategy returns, follow its `prompt` field when writing the
    final response. Its decision and analysis are authoritative; never change the
    decision or invent signals.
    """

    if tools:
        prompt += """
        You also have access to Zerodha Kite MCP tools. Use them for market and
        account data when relevant.
        """

    return create_agent(
        model=groq_model,
        tools=tools,
        system_prompt=prompt,
        middleware=[filter_tools],
    )
