import os

from lovelaice import Config

# --- 1. Models ---------------------------------------------------------------
# The first entry is the default; override at the CLI with `--model <alias>`.
# Add more aliases for different providers (cloud, local LM Studio, etc).
MODELS = {
    "default": {
        "model": "<default_model>",
        "api_key": os.getenv("API_KEY"),
        "base_url": "<base_url>",
    },
    # Example: a local LM Studio endpoint
    # "local": {
    #     "model": "qwen2.5-coder-14b-instruct",
    #     "api_key": "lm-studio",
    #     "base_url": "http://localhost:1234/v1",
    # },
}

# --- 2. System prompt --------------------------------------------------------
# Capabilities, tools, and the working directory are auto-injected at runtime;
# this is the place for high-level personality and house rules.
PROMPT = """
You are Lovelaice, a sovereign coding agent that runs in the user's terminal.
Be concise and act decisively. When a task is ambiguous, ask one focused
question instead of guessing. Prefer surgical edits over full rewrites.
""".strip()

# --- 3. Build the config -----------------------------------------------------
config = Config(models=MODELS, prompt=PROMPT)

# --- 4. Default tools (Pi-style: bash, read, write, edit, list) --------------
from lovelaice.tools import bash, read, write, edit, list_dir

config.tool(bash)
config.tool(read)
config.tool(write)
config.tool(edit)
config.tool(list_dir)

# --- 5. Default command: ReAct loop ------------------------------------------
from lovelaice.commands import react

config.command(react)

# --- 6. Custom tools and commands --------------------------------------------
# Use @config.tool and @config.command to register your own. Example:
#
# @config.tool
# async def search_notes(query: str) -> str:
#     """Search the user's notes for the given query."""
#     ...
#
# @config.command
# async def plan(context, engine):
#     """Produce a step-by-step plan before executing anything."""
#     ...
