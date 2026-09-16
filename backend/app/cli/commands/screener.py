from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from rich.console import Group
from rich.table import Table

from app.core.groq import groq_model
from app.core.stock import screen_stocks
from app.mcp.screener import FILTER_GUIDE


class ScanRequest(BaseModel):
    source: str = Field(description="A valid PatternsRadar Sift expression")
    universe: int = Field(default=500, ge=100, le=9999)
    limit: int = Field(default=20, ge=1, le=20)


def _display(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _table(
    result: dict, title: str, columns: tuple[tuple[str, str], ...]
) -> Table:
    table = Table(title=title)
    for _, label in columns:
        table.add_column(label)
    for row in result.get("rows", []):
        table.add_row(*(_display(row.get(key)) for key, _ in columns))
    return table


def scan_tables(result: dict) -> Group:
    selection_columns = (
        ("symbol", "Symbol"),
        ("name", "Company"),
        ("sector", "Sector"),
        ("close", "Close"),
        ("rsi_14", "RSI"),
        ("sma_50", "SMA 50"),
        ("sma_200", "SMA 200"),
        ("adx_14", "ADX"),
        ("rel_volume", "Rel. Volume"),
        ("delivery_pct", "Delivery %"),
        ("ret_1m", "1M %"),
        ("ret_1y", "1Y %"),
        ("marketcap", "Market Cap"),
    )
    context_columns = (
        ("symbol", "Symbol"),
        ("open", "Open"),
        ("high", "High"),
        ("low", "Low"),
        ("atr_14", "ATR"),
        ("volume", "Volume"),
        ("turnover", "Turnover"),
        ("ret_1d", "1D %"),
        ("ret_1w", "1W %"),
        ("ret_3m", "3M %"),
        ("high_52w", "52W High"),
        ("low_52w", "52W Low"),
        ("pct_from_52w_high", "% From 52W High"),
        ("has_fno", "F&O"),
    )
    status = "truncated" if result.get("truncated") else "complete"
    caption = f"{result.get('count', 0)} matches | as of {result.get('asOf', '-')} | {status}"
    selection = _table(result, "Stock Selection Signals", selection_columns)
    context = _table(result, "Supporting Market Context", context_columns)
    selection.caption = caption
    context.caption = caption
    return Group(selection, context)


async def define_screener(query: str) -> Group:
    if not query.strip():
        raise ValueError("Usage: /screener <filters to screen for>")

    parser = groq_model.with_structured_output(ScanRequest, method="json_mode")
    scan = ScanRequest.model_validate(
        await parser.ainvoke(
            [
                SystemMessage(
                    content=(
                        "Translate the user's screener request into a PatternsRadar "
                        "Sift scan request. Return one JSON object with only source, "
                        "universe, and limit. Never execute an API call and never "
                        "fabricate results.\n\n"
                        + FILTER_GUIDE
                    )
                ),
                HumanMessage(content=query),
            ]
        )
    )
    return scan_tables(await screen_stocks(scan.source, scan.universe, scan.limit))
