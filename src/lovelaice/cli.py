import asyncio
from datetime import datetime
import getpass
import inspect
import typer
from typing import Optional, List
from typing_extensions import Annotated
from pathlib import Path
from lingo.cli import loop

from rich.prompt import Prompt
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.markdown import Markdown

from dotenv import load_dotenv

from .security import SecurityManager
from .config import Config, find_config_file, load_agent_from_config
from .core import Lovelaice

load_dotenv()

app = typer.Typer(
    name="lovelaice",
    help="An extensible AI agent for your terminal",
    no_args_is_help=False,
)

console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    # Captures all positional arguments as the prompt
    prompt_parts: Annotated[
        Optional[List[str]],
        typer.Argument(help="The task or question for the agent", show_default=False),
    ] = None,
    # --- Administrative Actions ---
    init: Annotated[
        bool,
        typer.Option("--init", help="Initialize Lovelaice in the current directory"),
    ] = False,
    # --- Skills and Models ---
    skill: Annotated[
        Optional[str],
        typer.Option(
            "--skill", "-s", help="Specific skill to execute (e.g., plan, execute)"
        ),
    ] = None,
    model: Annotated[
        Optional[str],
        typer.Option("--model", "-m", help="Model alias from .lovelaice.py"),
    ] = None,
    # --- The Triad of Permissions ---
    read: Annotated[
        List[Path], typer.Option("--read", "-r", help="Paths allowed for reading")
    ] = [Path(".")],
    write: Annotated[
        List[Path], typer.Option("--write", "-w", help="Paths allowed for writing")
    ] = [],
    execute: Annotated[
        bool, typer.Option("--execute", "-x", help="Allow shell command execution")
    ] = False,
    # --- Scoping & Formatting ---
    input_files: Annotated[
        List[Path], typer.Option("--input", "-i", help="JIT Priority files")
    ] = [],
    output: Annotated[
        str,
        typer.Option("--output", "-o", help="Format: text, code, json, or schema.json"),
    ] = "text",
):
    """
    Lovelaice: Your sovereign AI thought partner.
    """
    # 1. Handle init first
    if init:
        config_path = Path(".lovelaice.py")
        if config_path.exists():
            typer.echo(f"❌ {config_path} already exists.", err=True)
            raise typer.Exit(code=1)

        # 1. Ask for configuration details interactively
        default_model = typer.prompt(
            "Enter the default model name", default="google/gemini-2.5-flash"
        )
        base_url = typer.prompt(
            "Enter the API base URL", default="https://openrouter.ai/api/v1"
        )

        # 2. Load the template source
        from lovelaice import template

        template_source = inspect.getsource(template)

        # 3. Format the template with user input
        # Note: We use .format() but must be careful with the double braces in the code
        formatted_source = template_source.replace(
            "<default_model>", default_model
        ).replace("<base_url>", base_url)

        # 4. Write to file
        config_path.write_text(formatted_source)
        typer.echo(
            f"✅ Initialized Lovelaice: {config_path} created with model '{default_model}'."
        )
        raise typer.Exit()

    security = SecurityManager(
        read_paths=read,
        write_paths=write,
        allow_execute=execute,
    )

    config_path = find_config_file()

    if not config_path:
        typer.echo("❌ No .lovelaice.py found. Run 'lovelaice --init' first.", err=True)
        raise typer.Exit(1)

    def on_token(token: str):
        print(token, end="", flush=True)

    try:
        config = load_agent_from_config(config_path)
        bot = config.build(model=model, on_token=on_token, security=security)
    except Exception as e:
        typer.echo(f"❌ Failed to load agent: {e}", err=True)
        raise typer.Exit(1)

    # 2. Reconstruct prompt
    prompt = " ".join(prompt_parts) if prompt_parts else ""

    if prompt:
        response_text = ""

        with Live(console=console, refresh_per_second=10) as live:

            def on_token(token: str):
                nonlocal response_text
                response_text += token
                # Update the panel content with rendered Markdown
                live.update(
                    Panel(
                        Markdown(response_text),
                        title="[bold blue]Lovelaice[/]",
                        border_style="blue",
                        expand=False,
                    )
                )

            config = load_agent_from_config(config_path)
            # Pass our custom system prompt and the token callback
            bot = config.build(model=model, on_token=on_token, security=security)

            asyncio.run(bot.chat(prompt))
    else:
        # Interactive mode logic...
        config = load_agent_from_config(config_path)
        asyncio.run(chat_loop(model, config, security))


class LiveChat:
    def __init__(self) -> None:
        self.response = ""
        self.live: Live = None

    def attach(self, live: Live):
        self.response = ""
        self.live = live

    def update(self, token):
        self.response += token
        self.live.update(
            Panel(
                Markdown(self.response),
                title="[bold blue]Lovelaice[/]",
                border_style="blue",
                expand=False,
            )
        )


async def chat_loop(model: str | None, config: Config, security: SecurityManager):
    """
    A stateful chat loop that renders user and assistant messages
    using Rich panels.
    """
    username = getpass.getuser()
    console.print(
        Panel(
            Markdown(
                f"Today is **{datetime.now().strftime('%A, %B %d')}**. Type `exit` or `quit` to stop."
            ),
            title="[bold]Lovelaice Session[/]",
            border_style="bright_black",
        )
    )

    console.print()

    chat = LiveChat()

    def on_token(token: str):
        chat.update(token)

    bot = config.build(model, on_token, security)

    while True:
        # 1. Get User Input
        try:
            user_input = Prompt.ask(f"[bold green]{username}[/]")
        except EOFError:  # Handle Ctrl+D
            break

        if user_input.lower() in ["exit", "quit"]:
            break

        # 2. Render Assistant Bubble and Stream Tokens
        console.print()

        with Live(
            console=console, refresh_per_second=10, vertical_overflow="visible"
        ) as live:
            chat.attach(live)
            await bot.chat(user_input)

        console.print()


if __name__ == "__main__":
    app()
