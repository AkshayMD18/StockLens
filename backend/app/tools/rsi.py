def rsi(data: dict) -> dict:
    values, period = data["values"], data.get("period", 14)
    if not isinstance(period, int) or isinstance(period, bool) or period <= 0:
        raise ValueError("Period must be a positive integer")
    if len(values) < period + 2:
        raise ValueError(f"Need at least {period + 2} values")
    gains = [max(current - previous, 0) for previous, current in zip(values, values[1:])]
    losses = [max(previous - current, 0) for previous, current in zip(values, values[1:])]
    average_gain, average_loss = sum(gains[:period]) / period, sum(losses[:period]) / period
    result: list[float | None] = [None] * period
    for gain, loss in zip(gains[period - 1 :], losses[period - 1 :]):
        if result[-1] is not None:
            average_gain = (average_gain * (period - 1) + gain) / period
            average_loss = (average_loss * (period - 1) + loss) / period
        result.append(100.0 if average_loss == 0 and average_gain else 50.0 if average_loss == 0 else 100 - 100 / (1 + average_gain / average_loss))
    return {"values": result, "value": result[-1], "previous_value": result[-2]}
