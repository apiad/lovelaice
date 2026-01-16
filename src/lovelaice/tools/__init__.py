from rich.console import Console
from rich.prompt import Prompt
from lingo import LLM, Message

console = Console()

async def confirm_action(tool_name: str, args: dict, llm: LLM) -> bool:
    """
    Standard confirmation loop for Lovelaice tools.
    Prompts the user for (y)es, (n)o, or (e)xplain.
    """
    console.print(f"\n[bold blue]🔧 Lovelaice Action: {tool_name}[/]")

    for key, value in args.items():
        # Truncate long values (like file content) for cleaner display
        display_val = str(value)
        if len(display_val) > 150:
            display_val = display_val[:150] + "..."
        console.print(f"  [dim]{key}: {display_val}[/]")

    while True:
        choice = Prompt.ask(
            "[bold yellow]Confirm?[/] (y)es / (n)o / (e)xplain",
            choices=["y", "n", "e"],
            default="y"
        )
        if choice == "y":
            return True
        if choice == "n":
            return False
        if choice == "e":
            # Request a semantic explanation from the injected LLM
            explanation_query = (
                f"You are the AI assistant Lovelaice. Explain in one or two sentences "
                f"exactly what the tool '{tool_name}' will do with these arguments: {args}."
            )
            response = await llm.chat([Message.user(explanation_query)])
