def sma(data: dict) -> dict:
    values, period = data["values"], data["period"]
    if period <= 0:
        raise ValueError("Period must be positive")
    if len(values) < period:
        raise ValueError(f"Need at least {period} values")
    result: list[float | None] = [None] * (period - 1)
    for index in range(period - 1, len(values)):
        result.append(sum(values[index - period + 1 : index + 1]) / period)
    return {"values": result, "value": result[-1]}
