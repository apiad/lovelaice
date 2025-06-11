import subprocess
from rich import get_console, print
from rich.prompt import Confirm


async def bash(code: str) -> str:
    """
    Run a bash one-liner.

    Make sure the `code` argument is a
    one-liner bash instruction.
    """
    if code.startswith("sudo"):
        print("[red]Warning: You are about to run a command with sudo.[/red]")

    print("Will run the following code:\n")

    if len(code.split("\n")) == 1:
        print("$ " + code)
    else:
        print(f"```bash\n{code}\n```")

    print()

    if Confirm.ask("Run the code?"):
        with get_console().status("Running code", spinner="dots"):
            result = subprocess.run(
                code, shell=True, capture_output=True, text=True, check=True
            )

        return result.stdout or "Script executed correctly."
    else:
        return "User aborted the script."
