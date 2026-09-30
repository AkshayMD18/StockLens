def crosses(data: dict, direction: str) -> dict:
    series_a, series_b = data["series_a"], data["series_b"]
    if len(series_a) != len(series_b):
        raise ValueError("Series must have equal lengths")
    if len(series_a) < 2:
        raise ValueError("Series must contain at least two values")
    previous_a, latest_a = series_a[-2:]
    previous_b, latest_b = series_b[-2:]
    if any(value is None for value in [previous_a, latest_a, previous_b, latest_b]):
        return {"value": False}
    if direction == "above":
        return {"value": previous_a <= previous_b and latest_a > latest_b}
    if direction == "below":
        return {"value": previous_a >= previous_b and latest_a < latest_b}
    raise ValueError(f"Invalid crossover direction: {direction}")
