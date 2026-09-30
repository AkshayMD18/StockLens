def calculate_signal(data: dict) -> dict:
    prices = data["prices"]
    if len(prices) < 2:
        raise ValueError("At least two prices are required")
    return {"signal": "buy" if prices[-1] > prices[-2] else "sell", "latest_price": prices[-1]}
