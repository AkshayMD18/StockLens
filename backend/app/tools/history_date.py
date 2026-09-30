from datetime import date
from typing import Any


def history_date(value: Any, today: date) -> Any:
    return today.isoformat() if value == "today" else value
