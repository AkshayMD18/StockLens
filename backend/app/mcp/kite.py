import asyncio
import logging
from contextlib import asynccontextmanager

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

logger = logging.getLogger("stocklens.kite")


@asynccontextmanager
async def session():
    client = MultiServerMCPClient(
        {
            "kite": {
                "url": "https://mcp.kite.trade/mcp",
                "transport": "streamable_http",
                "timeout": 60,
                "sse_read_timeout": 120,
                "terminate_on_close": False,
            }
        }
    )

    print("Loading Kite tools...", flush=True)
    try:
        async with client.session("kite") as kite_session:
            tools = await asyncio.wait_for(
                load_mcp_tools(kite_session, server_name="kite"), timeout=60
            )
            print(f"Loaded {len(tools)} Kite tools.", flush=True)
            yield tools
    except Exception as error:
        logger.exception("Kite tool discovery failed")
        raise RuntimeError(f"No Kite MCP tools loaded: {type(error).__name__}: {error}") from error
