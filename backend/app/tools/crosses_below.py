from app.tools.crosses import crosses


def crosses_below(data: dict) -> dict:
    return crosses(data, "below")
