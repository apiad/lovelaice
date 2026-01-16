import asyncio
from typing import List
from purely import depends
from lingo import LLM
from lovelaice.tools import confirm_action
from lovelaice.security import SecurityManager

async def execute_command(
    command: str,
    args: List[str],
    security = depends(SecurityManager),
    llm = depends(LLM)
) -> str:
    """
    Executes a shell command with a structured list of arguments.
    The 'command' must be whitelisted (e.g., 'git', 'ls', 'uv').
    """
    # 1. Security Check: Validate the base command against the whitelist
    if not security.can_execute(command):
        allowed = security.allow_execute if isinstance(security.allow_execute, list) else "all"
        return (
            f"❌ Permission Denied: The command '{command}' is not whitelisted.\n"
            f"Allowed commands: {allowed}"
        )

    # 2. Build the full command string for display and execution
    full_cmd = f"{command} {' '.join(args)}".strip()

    # 3. Confirmation + Explain Loop (y/n/e)
    # The 'e' option uses the injected LLM to explain the command's intent
    if not await confirm_action("execute_command", {"command": full_cmd}, llm):
        return "Action cancelled by user."

    # 4. Safe Asynchronous Execution
    try:
        process = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        output = []
        if stdout:
            output.append(f"--- STDOUT ---\n{stdout.decode().strip()}")
        if stderr:
            output.append(f"--- STDERR ---\n{stderr.decode().strip()}")

        return "\n\n".join(output) if output else "Command executed with no output."

    except FileNotFoundError:
        return f"❌ Error: Command '{command}' not found in system PATH."
    except Exception as e:
        return f"❌ Execution Error: {str(e)}"
