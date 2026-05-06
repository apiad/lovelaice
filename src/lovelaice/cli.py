import asyncio
import getpass
import inspect
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from typing_extensions import Annotated

from .config import Config, find_config_file, load_agent_from_config

load_dotenv()

app = typer.Typer(
    name="lovelaice",
    help="A local-first coding agent for the terminal.",
    no_args_is_help=False,
)

console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    prompt_parts: Annotated[
        Optional[List[str]],
        typer.Argument(help="The task or question for the agent.", show_default=False),
    ] = None,
    init: Annotated[
        bool,
        typer.Option("--init", help="Write a starter .lovelaice.py in the current directory."),
    ] = False,
    model: Annotated[
        Optional[str],
        typer.Option("--model", "-m", help="Named model alias from .lovelaice.py."),
    ] = None,
):
    """
    Lovelaice — your sovereign AI thought partner.

    With no arguments, opens an interactive chat loop. With a prompt,
    runs a single agentic turn and exits.
    """
    if init:
        _do_init()
        raise typer.Exit()

    config_path = find_config_file()
    if not config_path:
        typer.echo("No .lovelaice.py found. Run `lovelaice --init` first.", err=True)
        raise typer.Exit(1)

    prompt = " ".join(prompt_parts) if prompt_parts else ""

    if prompt:
        asyncio.run(_run_once(config_path, model, prompt))
    else:
        asyncio.run(_run_interactive(config_path, model))


def _do_init() -> None:
    config_path = Path(".lovelaice.py")
    if config_path.exists():
        typer.echo(f"{config_path} already exists.", err=True)
        raise typer.Exit(code=1)

    default_model = typer.prompt(
        "Default model name", default="google/gemini-2.5-flash"
    )
    base_url = typer.prompt(
        "API base URL", default="https://openrouter.ai/api/v1"
    )

    from lovelaice import template

    source = inspect.getsource(template)
    formatted = source.replace("<default_model>", default_model).replace(
        "<base_url>", base_url
    )
    config_path.write_text(formatted)
    typer.echo(f"Wrote {config_path} (default model: {default_model}).")


async def _run_once(config_path: Path, model: Optional[str], prompt: str) -> None:
    chat = _LiveChat()

    def on_token(token: str):
        chat.update(token)

    config = load_agent_from_config(config_path)
    bot = config.build(model=model, on_token=on_token)

    with Live(console=console, refresh_per_second=10, vertical_overflow="visible") as live:
        chat.attach(live)
        await bot.chat(prompt)


async def _run_interactive(config_path: Path, model: Optional[str]) -> None:
    username = getpass.getuser()
    console.print(
        Panel(
            Markdown(
                f"Today is **{datetime.now().strftime('%A, %B %d')}**. "
                "Type `exit` or `quit` (or Ctrl+D) to leave."
            ),
            title="[bold]Lovelaice[/]",
            border_style="bright_black",
        )
    )
    console.print()

    chat = _LiveChat()

    def on_token(token: str):
        chat.update(token)

    config = load_agent_from_config(config_path)
    bot = config.build(model=model, on_token=on_token)

    while True:
        try:
            user_input = Prompt.ask(f"[bold green]{username}[/]")
        except EOFError:
            break
        if user_input.lower() in ("exit", "quit"):
            break

        console.print()
        with Live(console=console, refresh_per_second=10, vertical_overflow="visible") as live:
            chat.attach(live)
            await bot.chat(user_input)
        console.print()


class _LiveChat:
    """Stream tokens into a single Rich live-rendered Markdown panel."""

    def __init__(self) -> None:
        self.response = ""
        self.live: Live | None = None

    def attach(self, live: Live) -> None:
        self.response = ""
        self.live = live

    def update(self, token: str) -> None:
        if self.live is None:
            return
        self.response += token
        self.live.update(
            Panel(
                Markdown(self.response),
                title="[bold blue]Lovelaice[/]",
                border_style="blue",
                expand=False,
            )
        )


if __name__ == "__main__":
    app()
