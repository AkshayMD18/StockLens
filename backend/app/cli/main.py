import logging
from pathlib import Path

from rich.panel import Panel

from app.agents.research import create_research_agent
from app.cli.commands.login import execute as kite_login
from app.cli.commands.screener import define_screener
from app.cli.commands.status import execute as kite_status
from app.cli.query import console, stream_reply
from app.mcp.kite import session as kite_session

LOG_FILE = Path(__file__).resolve().parents[2] / "stocklens_cli.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE)],
)
logger = logging.getLogger("stocklens.cli")


async def run(agent, kite_tools: list) -> None:
    messages: list[dict[str, str]] = []
    console.print(
        Panel(
            "[dim]/login[/], [dim]/status[/], [dim]/screener <filters>[/], [dim]/exit[/]",
            title="[bold cyan]StockLens[/]",
            border_style="cyan",
        )
    )

    while True:
        try:
            message = console.input("\n[bold green]You[/] [dim]>[/] ").strip()
        except EOFError, KeyboardInterrupt:
            console.print()
            return

        if message.lower() in {"/exit", "exit", "quit"}:
            return
        if message.lower() == "/login":
            try:
                console.print(
                    "[bold cyan]StockLens[/] [dim]>[/]",
                    await kite_login(kite_tools),
                )
            except Exception as error:
                logger.exception("kite_login_error")
                console.print(f"[bold red]Login failed:[/] {error}")
            continue
        if message.lower() == "/status":
            try:
                console.print(
                    "[bold cyan]StockLens[/] [dim]>[/]",
                    await kite_status(kite_tools),
                )
            except Exception as error:
                logger.exception("kite_status_error")
                console.print(f"[bold yellow]Not logged in:[/] {error}")
            continue
        if message.lower().startswith("/screener"):
            _, _, query = message.partition(" ")
            try:
                console.print(
                    "[bold cyan]StockLens[/] [dim]>[/]",
                    await define_screener(query),
                )
            except Exception as error:
                logger.exception("screener_error")
                console.print(f"[bold red]Screener failed:[/] {error}")
            continue
        if not message:
            continue

        messages.append({"role": "user", "content": message})
        console.print("[bold cyan]StockLens[/] [dim]>[/]")
        try:
            response = await stream_reply(agent, messages)
        except Exception as error:
            messages.pop()
            logger.exception("agent_error")
            console.print(f"[bold red]Error:[/] {error}")
            continue

        messages.append({"role": "assistant", "content": response})


async def main() -> None:
    try:
        async with kite_session() as kite_tools:
            with console.status("[cyan]Preparing StockLens...[/]"):
                agent = await create_research_agent(kite_tools)
            await run(agent, kite_tools)
    except Exception as error:
        console.print(f"[bold yellow]Kite tools unavailable:[/] {error}")
        await run(await create_research_agent(), [])
