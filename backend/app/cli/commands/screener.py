from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
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
        return "—"
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def scan_table(result: dict) -> Table:
    columns = (
        ("symbol", "Symbol"),
        ("name", "Company"),
        ("close", "Close"),
        ("rsi_14", "RSI"),
        ("rel_volume", "Rel. Volume"),
        ("ret_1d", "1D %"),
        ("ret_1m", "1M %"),
        ("marketcap", "Market Cap"),
        ("sector", "Sector"),
    )
    table = Table(title="PatternsRadar Screener Results")
    for _, label in columns:
        table.add_column(label)
    for row in result.get("rows", []):
        table.add_row(*(_display(row.get(key)) for key, _ in columns))
    status = "truncated" if result.get("truncated") else "complete"
    table.caption = (
        f"{result.get('count', 0)} matches · as of {result.get('asOf', '—')} · {status}"
    )
    return table


async def define_screener(query: str) -> Table:
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
    return scan_table(await screen_stocks(scan.source, scan.universe, scan.limit))
