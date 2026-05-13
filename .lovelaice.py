import os

from lovelaice import Config

# --- Models ---------------------------------------------------------------
# All models go through OpenRouter. The first entry is the default; pick
# another at runtime with `--model <alias>` (one-shot) or `/model` (TUI).
# Add `thinking="low"|"medium"|"high"` (or an int token budget) on a model
# entry to opt into reasoning passthrough.
MODELS = {
    "fast": {
        "model": "google/gemini-2.5-flash",
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "base_url": "https://openrouter.ai/api/v1",
    },
    # Example: a reasoning-enabled alias
    "pro": {
        "model": "~google/gemini-pro-latest",
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "base_url": "https://openrouter.ai/api/v1",
        "thinking": "high",
    },
}

# --- System prompt --------------------------------------------------------
PROMPT = """
You are Lovelaice, a sovereign coding agent that runs in the user's terminal.
Be concise and act decisively. When a task is ambiguous, ask one focused
question instead of guessing. Prefer surgical edits over full rewrites.
""".strip()

# --- Build the config -----------------------------------------------------
config = Config(
    models=MODELS,
    prompt=PROMPT,
    # mcp=[{"name": "...", "command": "...", "args": [...]}],
)

# --- Default tools --------------------------------------------------------
from lovelaice.tools import bash, read, write, edit, list_, glob, grep, fetch

config.tool(bash)
config.tool(read)
config.tool(write)
config.tool(edit)
config.tool(list_, name="list")
config.tool(glob)
config.tool(grep)
config.tool(fetch)

# --- Default command: ReAct loop ------------------------------------------
from lovelaice.commands import react

config.command(react)

# --- Custom tools and commands --------------------------------------------
# @config.tool
# async def search_notes(query: str) -> str:
#     """Search the user's notes for the given query."""
#     ...
