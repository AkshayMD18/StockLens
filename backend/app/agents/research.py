from langchain.agents import create_agent

from app.core.groq import groq_model
async def create_research_agent(tools: list | None = None):
    tools = tools or []

    prompt = """
    You are StockLens, a conversational stock research assistant.

    Once you have enough information, give the user a concise and useful answer.
    """

    if tools:
        prompt += """
        You have access to Zerodha Kite MCP tools. Use them for market and
        account data when relevant. Call the tool that matches the requested
        data and its documented inputs.
        Do not call tools unnecessarily.
        """

    agent = create_agent(model=groq_model, tools=tools, system_prompt=prompt)

    return agent
