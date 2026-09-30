from typing import Any


def kite_datetime(value: Any, end_of_day: bool) -> str:
    value = str(value)
    return value if " " in value else f"{value} {'23:59:59' if end_of_day else '00:00:00'}"
