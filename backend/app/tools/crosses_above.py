from app.tools.crosses import crosses


def crosses_above(data: dict) -> dict:
    return crosses(data, "above")
