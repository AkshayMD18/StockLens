async def execute(tools: list) -> object:
    profile_tool = next((tool for tool in tools if tool.name == "get_profile"), None)
    if profile_tool is None:
        raise RuntimeError("Kite profile tool is unavailable")
    return await profile_tool.ainvoke({})
