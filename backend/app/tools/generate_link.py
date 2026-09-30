def generate_link(data: dict) -> dict:
    return {"url": f"https://kite.zerodha.com/chart/web/ciq/{data['exchange']}/{data['symbol']}/{data['instrument_token']}"}
