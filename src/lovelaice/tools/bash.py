import asyncio


async def bash(command: str) -> str:
    """
    Run a shell command and return its combined stdout and stderr.

    Use this for any system-level action: inspecting the environment,
    running build tools, git operations, package management, scripts,
    quick one-liners, etc. The command is passed to the shell verbatim,
    so pipes, redirects, and variable expansion all work.
    """
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    parts = []
    if stdout:
        parts.append(stdout.decode("utf-8", errors="replace").rstrip())
    if stderr:
        parts.append(f"[stderr]\n{stderr.decode('utf-8', errors='replace').rstrip()}")

    body = "\n".join(parts) if parts else "(no output)"
    return f"$ {command}\n{body}\n[exit {process.returncode}]"
