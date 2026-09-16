import json
from typing import Any

from langchain_core.tools import tool

from app.core.stock import screen_stocks

SCAN_FIELDS = {
    "close",
    "open",
    "high",
    "low",
    "hl2",
    "hlc3",
    "ohlc4",
    "volume",
    "turnover",
    "trades",
    "delivery_pct",
    "delivery_qty",
    "rel_volume",
    "obv",
    "acc_dist",
    "cmf",
    "force_index",
    "stoch_k",
    "stoch_d",
    "stoch_rsi",
    "cci",
    "williams_r",
    "mfi",
    "roc",
    "adx",
    "di_plus",
    "di_minus",
    "supertrend",
    "supertrend_dir",
    "psar",
    "aroon_up",
    "aroon_down",
    "aroon_osc",
    "atr",
    "true_range",
    "bb_upper",
    "bb_mid",
    "bb_lower",
    "bb_pct_b",
    "bb_width",
    "donchian_upper",
    "donchian_mid",
    "donchian_lower",
    "keltner_upper",
    "keltner_lower",
    "change",
    "return_1w",
    "return_1m",
    "return_3m",
    "return_6m",
    "return_1y",
    "high_52w",
    "low_52w",
    "pct_from_52w_high",
    "marketcap",
    "pe",
    "eps_ttm",
    "revenue_growth_yoy",
    "profit_growth_yoy",
    "revenue_growth_qoq",
    "profit_growth_qoq",
    "promoter_pct",
    "public_pct",
    "fii_pct",
    "dii_pct",
    "promoter_pledged_pct",
    "promoter_change_qoq",
    "dividend_ttm",
    "dividend_yield",
    "dividend_growth_yoy",
    "dividend_streak_years",
    "universe_tier",
}

FILTER_GUIDE = f"""Run a PatternsRadar Sift scan against NSE equities.

Write a valid Sift `source` expression using these documented fields:
{", ".join(sorted(SCAN_FIELDS))}

Supported examples:
- `close > ema(21) > ema(50)`
- `rsi(14) > 70 and volume > 2x avg(volume, 20)`
- `delivery_pct > 60 and rel_volume > 2`
- `return_1m > 10 and close > sma(50)`
- `marketcap > 5000cr and pe < 30 and pe > 0`

Use `and` to combine conditions. Use `is` or `in` for sectors and industries,
for example `sector is "Information Technology"`. Indicators are functions:
use `rsi(14)`, `sma(50)`, `ema(21)`, `adx(14)`, and `atr(14)`, not response
column names such as `rsi_14` or `sma_50`. Percentage fields use percentage
points, so `return_1m > 10` means more than 10 percent. Use `universe` 100,
500, 2000, or 9999; 9999 scans all equities. `limit` must be between 1 and 20.
"""


@tool("screener", description=FILTER_GUIDE)
async def screener(
    source: str,
    universe: int = 500,
    limit: int = 20,
) -> Any:
    """Run one PatternsRadar Sift scan and return its JSON result."""
    return json.dumps(await screen_stocks(source, universe, limit), default=str)
