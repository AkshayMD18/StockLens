from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from typing import Any

import httpx


class _Tables(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None


def _empty(
    symbol: str, status: str, code: str | None = None, message: str | None = None
) -> dict:
    return {
        "symbol": symbol,
        "source": "screener.in",
        "status": status,
        "error": None if code is None else {"code": code, "message": message},
        "data": {
            "price": None,
            "pe": None,
            "book_value": None,
            "ev_to_ebitda": None,
            "roe": {"latest": None, "3y": None, "5y": None},
            "roce": [],
            "revenue": [],
            "net_profit": [],
            "eps": [],
            "borrowings": [],
            "equity_capital": [],
            "reserves": [],
            "operating_profit": [],
            "interest": [],
            "operating_cash_flow": [],
            "free_cash_flow": [],
            "promoter_holding": [],
            "promoter_pledge": None,
            "historical_pe": None,
            "industry_pe": None,
        },
    }


def _number(value: str) -> float | None:
    value = value.replace(",", "").replace("%", "").replace("₹", "").strip()
    if not value or value in {"-", "—"}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _table_with_row(
    tables: list[list[list[str]]], label: str
) -> list[list[str]] | None:
    return next(
        (table for table in tables if any(row and row[0] == label for row in table)),
        None,
    )


def _annual_table_with_row(
    tables: list[list[list[str]]], label: str
) -> list[list[str]] | None:
    return next(
        (
            table
            for table in tables
            if any(row and row[0] == label for row in table)
            and all(
                period.startswith("Mar ") or period == "TTM" for period in table[0][1:]
            )
        ),
        None,
    )


def _series(
    table: list[list[str]] | None, label: str
) -> list[dict[str, float | str | None]]:
    if table is None or not table:
        return []
    headers = table[0][1:]
    row = next((row for row in table[1:] if row and row[0] == label), None)
    if row is None:
        return []
    return [
        {"period": period, "value": _number(value)}
        for period, value in zip(headers, row[1:])
    ]


def _top_ratios(html: str) -> tuple[float | None, float | None, float | None]:
    text = " ".join(unescape(re.sub(r"<[^>]+>", " ", html)).split())
    return (
        _number_after(text, "Current Price"),
        _number_after(text, "Stock P/E"),
        _number_after(text, "Book Value"),
    )


def _number_after(text: str, label: str) -> float | None:
    match = re.search(rf"{re.escape(label)}\s*(?:₹\s*)?(-?[\d,]+(?:\.\d+)?)", text)
    return _number(match.group(1)) if match else None


def _roe(tables: list[list[list[str]]]) -> dict[str, float | None]:
    values = {"latest": None, "3y": None, "5y": None}
    table = next(
        (table for table in tables if table and table[0] == ["Return on Equity"]), None
    )
    if table is None:
        return values
    for key, label in (
        ("5y", "5 Years:"),
        ("3y", "3 Years:"),
        ("latest", "Last Year:"),
    ):
        row = next((row for row in table if row and row[0] == label), None)
        values[key] = _number(row[1]) if row and len(row) > 1 else None
    return values


async def screener_fundamentals(data: dict[str, Any]) -> dict:
    symbol = str(data.get("symbol", "")).strip().upper()
    if not symbol or not symbol.isalnum():
        return _empty(
            symbol, "unavailable", "invalid_symbol", "symbol must be alphanumeric"
        )

    url = f"https://www.screener.in/company/{symbol}/consolidated/"
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "StockLens/1.0"})
            response.raise_for_status()
    except httpx.HTTPStatusError as error:
        code = "not_found" if error.response.status_code == 404 else "http_error"
        return _empty(
            symbol,
            "unavailable",
            code,
            f"Screener returned HTTP {error.response.status_code}",
        )
    except httpx.RequestError as error:
        return _empty(symbol, "unavailable", "fetch_failed", str(error))

    parser = _Tables()
    parser.feed(response.text)
    profit_loss = _annual_table_with_row(parser.tables, "Sales +")
    if profit_loss is None:
        return _empty(
            symbol,
            "unavailable",
            "parse_failed",
            "Screener financial tables were unavailable",
        )

    result = _empty(symbol, "ok")
    fundamentals = result["data"]
    fundamentals["price"], fundamentals["pe"], fundamentals["book_value"] = _top_ratios(
        response.text
    )
    fundamentals["roe"] = _roe(parser.tables)
    fundamentals["revenue"] = _series(profit_loss, "Sales +")
    fundamentals["net_profit"] = _series(profit_loss, "Net Profit +")
    fundamentals["eps"] = _series(profit_loss, "EPS in Rs")
    fundamentals["operating_profit"] = _series(profit_loss, "Operating Profit")
    fundamentals["interest"] = _series(profit_loss, "Interest")
    balance_sheet = _table_with_row(parser.tables, "Borrowings +")
    fundamentals["borrowings"] = _series(balance_sheet, "Borrowings +")
    fundamentals["equity_capital"] = _series(balance_sheet, "Equity Capital")
    fundamentals["reserves"] = _series(balance_sheet, "Reserves")
    cash_flow = _table_with_row(parser.tables, "Cash from Operating Activity +")
    fundamentals["operating_cash_flow"] = _series(
        cash_flow, "Cash from Operating Activity +"
    )
    fundamentals["free_cash_flow"] = _series(cash_flow, "Free Cash Flow")
    ratios = _table_with_row(parser.tables, "ROCE %")
    fundamentals["roce"] = _series(ratios, "ROCE %")
    shareholding = _table_with_row(parser.tables, "Promoters +")
    fundamentals["promoter_holding"] = _series(shareholding, "Promoters +")
    return result
