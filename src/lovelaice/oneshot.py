"""One-shot mode: stream the agent's working transcript to stdout via Rich,
or emit just the final reply when stdout is piped.

When --verbose is passed, full tool result bodies are rendered. Without
it, tool calls render as one-line summaries only — the agent's final
reply is the user-facing payload.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import IO, Optional

from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel

from .config import load_agent_from_config


def _is_pipe(stream: IO) -> bool:
    """True if `stream` is not connected to a tty."""
    try:
        return not stream.isatty()
    except (AttributeError, ValueError):
        return True


async def run_oneshot(
    config_path: Path,
    *,
    model: Optional[str],
    prompt: str,
    verbose: bool,
) -> int:
    """Execute one agentic turn. Returns the desired process exit code."""
    pipe_mode = _is_pipe(sys.stdout)
    quiet = pipe_mode and not verbose

    # In verbose-pipe mode, send Rich output to stderr so stdout stays clean
    # for the final reply.
    console = Console(stderr=verbose and pipe_mode)

    reply_buffer: list[str] = []
    reasoning_buffer: list[str] = []

    def on_token(t: str) -> None:
        reply_buffer.append(t)

    def on_reasoning_token(t: str) -> None:
        reasoning_buffer.append(t)

    try:
        config = load_agent_from_config(config_path)
        bot = config.build(
            model=model,
            on_token=(lambda _t: None) if quiet else on_token,
            on_reasoning_token=(lambda _t: None) if quiet else on_reasoning_token,
        )
    except Exception as e:
        print(f"Failed to build agent: {e}", file=sys.stderr)
        return 2

    try:
        if quiet:
            result = await bot.chat(prompt)
            print(getattr(result, "content", "") or "", flush=True)
            return 0

        def render() -> Group | Panel:
            parts = []
            if reasoning_buffer:
                parts.append(Panel(
                    Markdown("".join(reasoning_buffer)),
                    title="[dim italic]thinking[/]",
                    border_style="bright_black",
                    expand=False,
                ))
            parts.append(Panel(
                Markdown("".join(reply_buffer) or " "),
                title="[bold blue]Lovelaice[/]",
                border_style="blue",
                expand=False,
            ))
            return parts[-1] if len(parts) == 1 else Group(*parts)

        with Live(console=console, refresh_per_second=12, vertical_overflow="visible") as live:
            async def pump_live() -> None:
                while True:
                    live.update(render())
                    await asyncio.sleep(1 / 12)

            pump_task = asyncio.create_task(pump_live())
            try:
                await bot.chat(prompt)
            finally:
                pump_task.cancel()
                try:
                    await pump_task
                except asyncio.CancelledError:
                    pass
                live.update(render())
        return 0
    except asyncio.TimeoutError:
        print("LLM call timed out", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"LLM error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
