from rich.markdown import Markdown


async def kite_login(tools: list) -> object:
    login_tool = next((tool for tool in tools if tool.name == "login"), None)
    if login_tool is None:
        raise RuntimeError("Kite login tool is unavailable")
    response = await login_tool.ainvoke({})
    text = next(
        (item.get("text", "") for item in response if isinstance(item, dict)),
        str(response),
    )
    return Markdown(text)
