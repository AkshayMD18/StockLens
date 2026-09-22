import json

from rich.table import Table


async def kite_status(tools: list) -> object:
    profile_tool = next((tool for tool in tools if tool.name == "get_profile"), None)
    if profile_tool is None:
        raise RuntimeError("Kite profile tool is unavailable")
    response = await profile_tool.ainvoke({})
    text = next(
        (item.get("text", "") for item in response if isinstance(item, dict)),
        str(response),
    )
    profile = json.loads(text)
    table = Table(title="Kite Account")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    for key in ("user_id", "user_name", "email", "broker", "user_type"):
        table.add_row(key.replace("_", " ").title(), str(profile.get(key, "-")))
    table.add_row("Products", ", ".join(profile.get("products", [])))
    table.add_row("Exchanges", ", ".join(profile.get("exchanges", [])))
    return table
