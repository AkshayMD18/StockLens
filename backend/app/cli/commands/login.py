async def execute(tools: list) -> object:
    login_tool = next((tool for tool in tools if tool.name == "login"), None)
    if login_tool is None:
        raise RuntimeError("Kite login tool is unavailable")
    return await login_tool.ainvoke({})
