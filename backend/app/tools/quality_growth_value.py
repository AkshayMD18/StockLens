from typing import Any


def _latest(series: list[dict]) -> float | None:
    values = [item.get("value") for item in series if isinstance(item.get("value"), (int, float))]
    return float(values[-1]) if values else None


def _values(series: list[dict]) -> list[float]:
    return [float(item["value"]) for item in series if isinstance(item.get("value"), (int, float))]


def _annual(series: list[dict]) -> list[float]:
    return [
        float(item["value"])
        for item in series
        if item.get("period") != "TTM" and isinstance(item.get("value"), (int, float))
    ]


def _cagr(series: list[dict]) -> float | None:
    values = _annual(series)
    if len(values) < 4 or values[-4] <= 0 or values[-1] <= 0:
        return None
    return ((values[-1] / values[-4]) ** (1 / 3) - 1) * 100


def _average(values: list[float]) -> float:
    return sum(values) / len(values)


def _near(price: float | None, average: float | None) -> bool:
    return price is not None and average is not None and abs(price - average) / average <= 0.03


def quality_growth_value(data: dict[str, Any]) -> dict[str, Any]:
    fundamentals = data.get("fundamentals") if isinstance(data.get("fundamentals"), dict) else {}
    closes = [float(value) for value in data.get("closes", []) if isinstance(value, (int, float))]
    warnings: list[str] = []

    roe = fundamentals.get("roe") if isinstance(fundamentals.get("roe"), dict) else {}
    roe_3y, roe_5y = roe.get("3y"), roe.get("5y")
    roce_history = _annual(fundamentals.get("roce", []))[-3:]
    roce_latest = roce_history[-1] if roce_history else None
    roce_average = _average(roce_history) if roce_history else None
    roce_minimum = min(roce_history) if roce_history else None
    roce_consistent = bool(roce_history) and all(value >= 15 for value in roce_history)
    quality_pass = (
        roe_3y is not None and roe_3y >= 15
        and (roe_5y is None or roe_5y >= 15)
        and len(roce_history) == 3 and roce_average is not None and roce_average >= 15
        and roce_latest is not None and roce_latest >= 15
    )
    if roce_average is not None and roce_average >= 15 and not roce_consistent:
        warnings.append("roce_inconsistent")

    revenue_cagr = _cagr(fundamentals.get("revenue", []))
    profit_cagr = _cagr(fundamentals.get("net_profit", []))
    eps_cagr = _cagr(fundamentals.get("eps", []))
    growth_pass = all(value is not None and value >= 10 for value in (revenue_cagr, profit_cagr, eps_cagr))

    debt = _latest(fundamentals.get("borrowings", []))
    equity = _latest(fundamentals.get("equity_capital", []))
    reserves = _latest(fundamentals.get("reserves", []))
    debt_to_equity = debt / (equity + reserves) if debt is not None and equity is not None and reserves is not None and equity + reserves > 0 else None
    operating_profit = _latest(fundamentals.get("operating_profit", []))
    interest = _latest(fundamentals.get("interest", []))
    interest_coverage = operating_profit / interest if operating_profit is not None and interest is not None and interest > 0 else None
    health_pass = debt_to_equity is not None and debt_to_equity <= 0.5 and interest_coverage is not None and interest_coverage >= 3

    operating_cash_flow = _latest(fundamentals.get("operating_cash_flow", []))
    free_cash_flow = _latest(fundamentals.get("free_cash_flow", []))
    fcf_trend = _annual(fundamentals.get("free_cash_flow", []))[-3:]
    repeated_negative = any(left < 0 and right < 0 for left, right in zip(fcf_trend, fcf_trend[1:]))
    deteriorating_fcf = len(fcf_trend) == 3 and fcf_trend[0] > fcf_trend[1] > fcf_trend[2]
    if repeated_negative:
        warnings.append("repeated_negative_free_cash_flow")
    if deteriorating_fcf:
        warnings.append("deteriorating_free_cash_flow")

    pe, price, book_value = fundamentals.get("pe"), fundamentals.get("price"), fundamentals.get("book_value")
    historical_pe, industry_pe, ev_to_ebitda = fundamentals.get("historical_pe"), fundamentals.get("industry_pe"), fundamentals.get("ev_to_ebitda")
    price_to_book = price / book_value if isinstance(price, (int, float)) and isinstance(book_value, (int, float)) and book_value > 0 else None
    earnings_yield = 100 / pe if isinstance(pe, (int, float)) and pe > 0 else None
    peg = pe / eps_cagr if isinstance(pe, (int, float)) and pe > 0 and eps_cagr is not None and eps_cagr > 0 else None
    if eps_cagr is not None and eps_cagr <= 0:
        warnings.append("peg_not_meaningful_due_to_negative_growth")
    for key, value in (("historical_pe_unavailable", historical_pe), ("industry_pe_unavailable", industry_pe), ("price_to_book_unavailable", price_to_book), ("ev_to_ebitda_unavailable", ev_to_ebitda)):
        if value is None:
            warnings.append(key)

    promoter_history = _values(fundamentals.get("promoter_holding", []))
    promoter_current = promoter_history[-1] if promoter_history else None
    promoter_previous = promoter_history[-2] if len(promoter_history) >= 2 else None
    promoter_change = promoter_current - promoter_previous if promoter_current is not None and promoter_previous is not None else None
    promoter_pledge = fundamentals.get("promoter_pledge")
    if len(promoter_history) < 2:
        warnings.append("promoter_holding_history_unavailable")
    elif promoter_change is not None and promoter_change < 0:
        warnings.append("promoter_holding_decreased")
    if promoter_pledge is None:
        warnings.append("promoter_pledge_unavailable")
    elif promoter_pledge > 0:
        warnings.append("promoter_pledge_present")

    fundamental_status = "PASS" if quality_pass and growth_pass and health_pass else "REJECT"
    latest_price = closes[-1] if closes else price
    dma_50 = _average(closes[-50:]) if len(closes) >= 50 else None
    dma_200 = _average(closes[-200:]) if len(closes) >= 200 else None
    prior_dma_200 = _average(closes[-220:-20]) if len(closes) >= 220 else None
    dma_200_slope = dma_200 - prior_dma_200 if dma_200 is not None and prior_dma_200 is not None else None
    long_term_uptrend = (
        latest_price is not None and dma_50 is not None and dma_200 is not None and dma_200_slope is not None
        and latest_price > dma_200 and dma_50 > dma_200 and dma_200_slope > 0
    )
    near_50_dma, near_200_dma = _near(latest_price, dma_50), _near(latest_price, dma_200)
    potential_entry = fundamental_status == "PASS" and long_term_uptrend and (near_50_dma or near_200_dma)

    if not quality_pass:
        warnings.append("quality_threshold_not_met")
    if not growth_pass:
        warnings.append("growth_threshold_not_met")
    if not health_pass:
        warnings.append("financial_health_threshold_not_met")
    if not long_term_uptrend:
        warnings.append("long_term_uptrend_not_confirmed")
    has_position = data.get("has_position") is True
    decision = "REVIEW_EXIT" if fundamental_status == "REJECT" and has_position else "REJECT" if fundamental_status == "REJECT" else "BUY_CANDIDATE" if potential_entry else "WAIT"

    return {
        "fundamental_status": fundamental_status,
        "decision": decision,
        "quality": {"roe_3y": roe_3y, "roe_5y": roe_5y, "roce": {"latest": roce_latest, "average_3y": roce_average, "minimum_3y": roce_minimum, "history_3y": roce_history, "roce_consistent": roce_consistent}},
        "growth": {"revenue_cagr_3y": revenue_cagr, "profit_cagr_3y": profit_cagr, "eps_cagr_3y": eps_cagr},
        "financial_health": {"debt_to_equity": debt_to_equity, "interest_coverage": interest_coverage},
        "cash_flow": {"operating_cash_flow": operating_cash_flow, "free_cash_flow": free_cash_flow, "free_cash_flow_trend": fcf_trend, "positive_free_cash_flow": free_cash_flow is not None and free_cash_flow > 0, "repeated_negative_free_cash_flow": repeated_negative, "deteriorating_free_cash_flow": deteriorating_fcf},
        "valuation": {"pe": pe, "historical_pe": historical_pe, "industry_pe": industry_pe, "price_to_book": price_to_book, "ev_to_ebitda": ev_to_ebitda, "earnings_yield": earnings_yield, "peg": peg},
        "ownership": {"promoter_holding_current": promoter_current, "promoter_holding_previous": promoter_previous, "promoter_holding_change": promoter_change, "promoter_holding_history": promoter_history, "promoter_pledge": promoter_pledge},
        "trend": {"latest_price": latest_price, "dma_50": dma_50, "dma_200": dma_200, "dma_200_slope": dma_200_slope, "long_term_uptrend": long_term_uptrend},
        "entry": {"near_50_dma": near_50_dma, "near_200_dma": near_200_dma, "potential_entry": potential_entry},
        "warnings": warnings,
    }
