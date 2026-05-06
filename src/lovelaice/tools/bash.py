"""Bash tool: yolo subprocess execution with a configurable timeout.

`Config(bash_timeout=...)` mutates `BASH_TIMEOUT` at build-time; the
default is 120 seconds.
"""
from __future__ import annotations

import asyncio


BASH_TIMEOUT: float = 120.0


async def bash(command: str) -> str:
    """
    Run `command` in a shell. Returns combined stdout+stderr in invocation
    order. Nonzero exit codes do not raise — the output is returned and the
    agent decides what to do.

    Times out after BASH_TIMEOUT seconds; on timeout, the subprocess is
    SIGTERM'd (then SIGKILL'd 1 second later if still alive) and a
    TimeoutError is raised.
    """
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=BASH_TIMEOUT)
    except asyncio.TimeoutError:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
        raise TimeoutError(f"bash timed out after {BASH_TIMEOUT}s")

    return stdout.decode("utf-8", errors="replace")
