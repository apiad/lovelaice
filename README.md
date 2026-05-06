# Lovelaice

A sovereign, local-first coding agent for the terminal. Single ReAct
loop over a small built-in tool set, yolo by default. Two modes:

- **Interactive** — full-screen Textual TUI: `lovelaice`
- **One-shot**   — streams to stdout and exits: `lovelaice <prompt>`

## Install

```bash
pipx install lovelaice
```

## Configure

`lovelaice --init` writes a `.lovelaice.py` in the current directory.
This file *grounds the workspace*: when you run `lovelaice` from any
subdirectory, it walks up to the nearest `.lovelaice.py` and `chdir`s
to its directory before running. Exactly one config grounds the
workspace — there is no stacking.

Set `OPENROUTER_API_KEY` in your environment before running.

```bash
export OPENROUTER_API_KEY=sk-or-...
lovelaice
```

## Commands and tools

The `.lovelaice.py` registers tools and commands as decorators on a
`Config` object. Built-in tools: `bash`, `read`, `write`, `edit`,
`list`, `glob`, `grep`, `fetch`. Add your own with `@config.tool`.
See `know-how/writing-a-tool.md` and `know-how/writing-a-command.md`.

## Thinking mode

Add `thinking="high"` (or `"low"`/`"medium"`, or an integer token
budget) on a model entry to enable OpenRouter's reasoning passthrough.
Reasoning chunks render in a separate dim-italic panel above the
agent's reply. Non-OpenRouter base URLs silently ignore the knob —
v1 does not translate reasoning protocols across providers.

## MCP

Pass `mcp=[...]` to `Config(...)` to spawn stdio MCP servers and
register their tools. Tool names are prefixed `mcp:<server>:<tool>`.

```python
config = Config(
    models=MODELS,
    prompt=PROMPT,
    mcp=[
        {"name": "filesystem", "command": "npx",
         "args": ["@modelcontextprotocol/server-filesystem", "."]},
    ],
)
```

## License

MIT.
