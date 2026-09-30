def vwap(data: dict) -> dict:
    high, low, close, volume = data["high"], data["low"], data["close"], data["volume"]
    if not (len(high) == len(low) == len(close) == len(volume)):
        raise ValueError("VWAP series must have equal lengths")
    if not close or any(value < 0 for value in volume):
        raise ValueError("VWAP requires candles and non-negative volume")
    cumulative_pv = cumulative_volume = 0.0
    result = []
    for high_value, low_value, close_value, volume_value in zip(high, low, close, volume):
        cumulative_pv += ((high_value + low_value + close_value) / 3) * volume_value
        cumulative_volume += volume_value
        result.append(cumulative_pv / cumulative_volume if cumulative_volume else None)
    return {"values": result, "value": result[-1]}
