from typing import Any


def response_text(value: Any) -> str:
    if isinstance(value, str): return value
    if isinstance(value, dict):
        text = value.get("text")
        return text if isinstance(text, str) else " ".join(filter(None, (response_text(item) for item in value.values())))
    if isinstance(value, list): return " ".join(filter(None, (response_text(item) for item in value)))
    return ""
