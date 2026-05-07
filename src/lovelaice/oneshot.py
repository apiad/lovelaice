"""One-shot mode: stream a single agentic turn to stdout/stderr in one
of three output formats:

- ``rich`` (default) — Rich Live transcript with reasoning and reply
  panels. When stdout is piped (no --verbose), drops down to a "quiet"
  variant that prints just the final reply text on stdout.
- ``plain`` — raw streaming text. Content tokens go to stdout, reasoning
  tokens go to stderr. No Rich, no panels, no markup. Pipeline-friendly.
- ``json`` — newline-delimited JSON event stream on stdout. One event
  per line: ``reasoning``, ``content``, ``done``, ``error``. Programmatic
  consumers (tests, automation, frontends) should use this mode.

The mode is selected by the CLI via mutually-exclusive ``--plain`` /
``--json`` flags; without either, ``rich`` is used.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import IO, Literal, Optional

from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel

from .config import load_agent_from_config


OutputMode = Literal["rich", "plain", "json"]


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
    verbose: bool = False,
    output: OutputMode = "rich",
) -> int:
    """Execute one agentic turn. Returns the desired process exit code."""
    if output == "json":
        return await _run_json(config_path, model=model, prompt=prompt)
    if output == "plain":
        return await _run_plain(config_path, model=model, prompt=prompt)
    return await _run_rich(config_path, model=model, prompt=prompt, verbose=verbose)


# --- json mode ----------------------------------------------------------


async def _run_json(config_path: Path, *, model: Optional[str], prompt: str) -> int:
    """NDJSON event stream on stdout. Best for tests and frontends."""

    def emit(event: dict) -> None:
        sys.stdout.write(json.dumps(event, ensure_ascii=False) + "\n")
        sys.stdout.flush()

    def on_token(t: str) -> None:
        emit({"type": "content", "delta": t})

    def on_reasoning_token(t: str) -> None:
        emit({"type": "reasoning", "delta": t})

    try:
        config = load_agent_from_config(config_path)
        bot = config.build(
            model=model,
            on_token=on_token,
            on_reasoning_token=on_reasoning_token,
        )
    except Exception as e:
        emit({"type": "error", "stage": "build", "message": str(e)})
        return 2

    try:
        result = await bot.chat(prompt)
        emit({"type": "done", "content": getattr(result, "content", "") or ""})
        return 0
    except asyncio.TimeoutError:
        emit({"type": "error", "stage": "chat", "message": "timeout"})
        return 2
    except Exception as e:
        emit({
            "type": "error",
            "stage": "chat",
            "message": f"{type(e).__name__}: {e}",
        })
        return 2


# --- plain mode ---------------------------------------------------------


async def _run_plain(config_path: Path, *, model: Optional[str], prompt: str) -> int:
    """Raw streaming text. Content → stdout, reasoning → stderr."""

    def on_token(t: str) -> None:
        sys.stdout.write(t)
        sys.stdout.flush()

    def on_reasoning_token(t: str) -> None:
        sys.stderr.write(t)
        sys.stderr.flush()

    try:
        config = load_agent_from_config(config_path)
        bot = config.build(
            model=model,
            on_token=on_token,
            on_reasoning_token=on_reasoning_token,
        )
    except Exception as e:
        print(f"Failed to build agent: {e}", file=sys.stderr)
        return 2

    try:
        await bot.chat(prompt)
        # Trailing newlines so shells and pipes don't end mid-line.
        sys.stdout.write("\n")
        sys.stdout.flush()
        sys.stderr.write("\n")
        sys.stderr.flush()
        return 0
    except asyncio.TimeoutError:
        print("\nLLM call timed out", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"\nLLM error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


# --- rich mode ----------------------------------------------------------


async def _run_rich(
    config_path: Path,
    *,
    model: Optional[str],
    prompt: str,
    verbose: bool,
) -> int:
    """Rich Live transcript. Falls back to bare-stdout 'quiet' mode when
    stdout is piped and --verbose was not requested, so shell pipelines
    get clean output."""
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
