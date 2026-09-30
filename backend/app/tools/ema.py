def ema(data: dict) -> dict:
    values, period = data["values"], data["period"]
    if period <= 0:
        raise ValueError("Period must be positive")
    if len(values) < period:
        raise ValueError(f"Need at least {period} values")
    alpha = 2 / (period + 1)
    previous_ema = sum(values[:period]) / period
    result: list[float | None] = [None] * (period - 1) + [previous_ema]
    for value in values[period:]:
        previous_ema = value * alpha + previous_ema * (1 - alpha)
        result.append(previous_ema)
    return {"values": result, "value": result[-1]}
