# AGENTS.md — lovelaice

A sovereign, local-first terminal coding agent. Single ReAct loop on
top of `lingo`, with a Textual TUI for interactive mode and a Rich-
streamed one-shot mode.

## Quick orientation

- `src/lovelaice/cli.py` — typer entrypoint. Resolves the workspace
  root (chdir to the nearest ancestor `.lovelaice.py`) and dispatches
  to either `oneshot.py` (one-shot) or `tui/app.py` (interactive).
- `src/lovelaice/config.py` — `Config` plugin registry. Loaded by
  evaluating the user's `.lovelaice.py`.
- `src/lovelaice/core.py` — `Lovelaice(Lingo)` injects the env-status
  block on every turn and forwards a `_on_tool_call` hook through to
  the running `Engine`.
- `src/lovelaice/thinking.py` — `ThinkingLLM` adds OpenRouter
  reasoning passthrough on top of `lingo.LLM`. Plain `lingo.LLM` is
  used when no `thinking=` knob is set or the base URL is not
  OpenRouter.
- `src/lovelaice/mcp.py` — spawns stdio MCP servers in a background
  asyncio loop and wraps their tools as `lingo.Tool`s named
  `mcp:<server>:<tool>`. Calls bridge across the threads via
  `asyncio.run_coroutine_threadsafe`.
- `src/lovelaice/commands/react.py` — the default command (decide /
  equip / invoke loop, with a `_lovelaice_on_tool_call` hook).
- `src/lovelaice/tools/` — built-in tools.
  - `bash.py` (with `BASH_TIMEOUT`)
  - `files.py` (`read`, `write`, `edit`, `list_` — registered as
    `list` by the template)
  - `search.py` (`glob`, `grep`, both gitignore-aware)
  - `web.py` (`fetch`)
- `src/lovelaice/tui/` — Textual app, transcript widget, blocks.
- `src/lovelaice/oneshot.py` — Rich-driven one-shot mode with
  isatty-based pipe detection.

## Running tests

```bash
uv run pytest
```

## Know-how

Specific procedure docs in `know-how/`. Match the task; load the
matching doc.

- **writing-a-tool** — when adding a new built-in or custom tool.
- **writing-a-command** — when adding an agent-side workflow command.

## Manual smoke checklist

The TUI is hard to fully unit-test. Before tagging a release,
manually smoke:

- `lovelaice --init` in an empty dir → produces a working
  `.lovelaice.py`.
- `lovelaice "list the files"` (with `OPENROUTER_API_KEY` set) →
  tool call rendered, final reply streams in a Rich panel.
- `echo nothing | lovelaice "say hi" | wc -l` → only the final reply
  on stdout (pipe mode).
- `lovelaice` (no arg) → TUI launches; `/help` shows help; submit a
  message; `Ctrl+C` cancels; `/exit` quits.
- A `.lovelaice.py` with `thinking="high"` on a model alias → the
  thinking panel renders during streaming.
