import asyncio
import inspect
import os
from pathlib import Path
from typing import List, Optional

import typer
from dotenv import load_dotenv
from typing_extensions import Annotated

from .config import find_config_file

load_dotenv()

app = typer.Typer(
    name="lovelaice",
    help="A local-first coding agent for the terminal.",
    no_args_is_help=False,
)


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
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show full tool output (one-shot mode)."),
    ] = False,
):
    """
    Lovelaice — a sovereign coding agent for the terminal.

    With no arguments, opens a full-screen TUI. With a prompt, runs a
    single agentic turn and streams to stdout.
    """
    if init:
        _do_init()
        raise typer.Exit()

    config_path = find_config_file()
    if config_path is None:
        typer.echo(
            "No .lovelaice.py found in this directory or any ancestor. "
            "Run `lovelaice --init` to create one.",
            err=True,
        )
        raise typer.Exit(1)

    # Ground the workspace: chdir to where .lovelaice.py lives, then load
    # it by basename so any relative imports in the config see the new cwd.
    os.chdir(config_path.parent)
    config_path = Path(".lovelaice.py")

    prompt = " ".join(prompt_parts) if prompt_parts else ""

    if prompt:
        from .oneshot import run_oneshot
        rc = asyncio.run(run_oneshot(config_path, model=model, prompt=prompt, verbose=verbose))
        raise typer.Exit(rc)
    else:
        from .tui.app import run_tui
        asyncio.run(run_tui(config_path, model=model))


def _do_init() -> None:
    config_path = Path(".lovelaice.py")
    if config_path.exists():
        typer.echo(f"{config_path} already exists.", err=True)
        raise typer.Exit(code=1)

    default_model = typer.prompt(
        "Default model name", default="google/gemini-2.5-flash"
    )
    base_url = typer.prompt(
        "OpenRouter API base URL", default="https://openrouter.ai/api/v1"
    )

    from lovelaice import template

    source = inspect.getsource(template)
    formatted = source.replace("<default_model>", default_model).replace(
        "<base_url>", base_url
    )
    config_path.write_text(formatted)
    typer.echo(f"Wrote {config_path} (default model: {default_model}).")
    typer.echo("Set OPENROUTER_API_KEY in your environment before running lovelaice.")


if __name__ == "__main__":
    app()
