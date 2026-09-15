import logging
import sys
from pathlib import Path

from app.agents.research import create_research_agent
from app.cli.commands.login import execute as kite_login
from app.cli.commands.status import execute as kite_status
from app.cli.query import stream_reply
from app.mcp.kite import session as kite_session

LOG_FILE = Path(__file__).resolve().parents[2] / "stocklens_cli.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("stocklens.cli")


async def run(agent, kite_tools: list) -> None:
    messages: list[dict[str, str]] = []
    print("StockLens CLI with Kite tools. Commands: /login, /status, /exit.")

    while True:
        try:
            message = input("\nYou > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if message.lower() in {"/exit", "exit", "quit"}:
            return
        if message.lower() == "/login":
            try:
                print(f"StockLens > {await kite_login(kite_tools)}")
            except Exception as error:
                logger.exception("kite_login_error")
                print(f"StockLens > Login failed: {error}")
            continue
        if message.lower() == "/status":
            try:
                print(f"StockLens > {await kite_status(kite_tools)}")
            except Exception as error:
                logger.exception("kite_status_error")
                print(f"StockLens > Not logged in: {error}")
            continue
        if not message:
            continue

        messages.append({"role": "user", "content": message})
        print("StockLens > ", end="", flush=True)
        try:
            response = await stream_reply(agent, messages)
        except Exception as error:
            messages.pop()
            logger.exception("agent_error")
            print(f"\nError: {error}")
            continue

        messages.append({"role": "assistant", "content": response})


async def main() -> None:
    print("Connecting to Kite tools...", flush=True)
    try:
        async with kite_session() as kite_tools:
            await run(await create_research_agent(kite_tools), kite_tools)
    except Exception as error:
        print(f"Kite tools are unavailable; continuing without them: {error}")
        await run(await create_research_agent(), [])
