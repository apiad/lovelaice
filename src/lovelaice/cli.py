import inspect
import typer
from typing import Optional, List
from typing_extensions import Annotated
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

app = typer.Typer(
    name="lovelaice",
    help="An extensible AI agent for your terminal",
    no_args_is_help=False,
)


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
            "Enter the default model name", default="gemini-2.0-flash"
        )
        base_url = typer.prompt(
            "Enter the API base URL", default="https://openrouter.io/api/v1"
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

    # 2. Reconstruct the prompt from parts
    prompt = " ".join(prompt_parts) if prompt_parts else ""

    # 3. Execution Logic (Mocked for now)
    if skill:
        typer.echo(f"🛠️ Executing skill: {skill}")

    if prompt:
        typer.echo(f"🤖 Processing: {prompt}")
    elif not skill:
        typer.echo("Lovelaice is active. Use --help for options or type a task.")


if __name__ == "__main__":
    app()
