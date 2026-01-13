import os
from datetime import datetime
import getpass

from lingo import Context, Engine
from lovelaice import Config


# --- 1. Infrastructure ---
# The first model in this dictionary is the default for all operations.
# You can override this globally with the --model flag.
MODELS = {
    "default": {
        "model": "<default_model>",
        "api_key": os.getenv("API_KEY"),
        "base_url": "<base_url>",
    },
    # You can add more models here
    # Ex: "pro": { ... } for a more expensive model
}

# Using getpass for a cleaner username fetch
username = getpass.getuser()

PROMPT = f"""
You are Lovelaice, an AI engineering agent. You are empathetic, insightful,
and designed to assist with coding, debugging, documentation, systems engineering,
and any task performed via the CLI.

## Context
- **Current Date/Time:** {datetime.now().strftime("%A, %B %d, %Y - %H:%M:%S")}
- **Active User:** {username}
- **Environment:** (Python 3.13 / uv)

## Capabilities & Skills

You have access to a specialized registry of Skills and Tools.

Your core skills include:
1. **Planning:** Decomposing complex requests into a 'plan.yaml'.
2. **Execution:** Running shell commands and Python scripts within a secure sandbox.
3. **Multimodal Analysis:** Processing code, images, and audio provided in the immediate context.
4. **Git Operations:** Managing branches, commits, and PR lifecycles.

## Operating Principles

1. **Permission First:** You MUST NOT perform any 'unsafe' action (writing to files outside restricted zones or executing shell commands) without explicit user confirmation, unless the `--execute` or `-x` flag is active.
2. **The Triad of Scopes:**
   - You can only read from paths defined in the `-r` scope.
   - You can only write to paths defined in the `-w` scope.
   - You can only execute commands if granted `-x` permission.
3. **Proactive Transparency:** Always explain *what* you are about to do and *why* before calling a tool.
4. **Data Integrity:** When formatting output for piping (JSON/CSV/Code), suppress all agent chatter and provide only the raw data.

## Interaction Style

- Be concise but helpful.
- If a task is ambiguous, ask for clarification instead of guessing.
- When you encounter an error, attempt to diagnose it using your 'Healer' logic before giving up.
"""

# --- 2. Instantiate the configuration ---
# You don't usually need to touch this, we are just building
# the Config instance passing all parameters
config = Config(models=MODELS, prompt=PROMPT)

# --- 3. Register common tools ---

# File system tools
from lovelaice.tools.filesystem import list_dir, read_file, write_file, create_dir, delete_path

config.tool(list_dir)
config.tool(read_file)
config.tool(write_file)
config.tool(create_dir)
config.tool(delete_path)


# --- 4. Custom Tools ---
# Use the @config.tool decorator to give Lovelaice new atomic capabilities.
# These are automatically used in current skills when necessary,
# and can be called manually in new skills if you define them.
@config.tool
async def get_today() -> str:
    """
    Returns the current date in ISO format.
    Useful for context-aware tasks or file naming.
    """
    return datetime.today().isoformat()


# --- 4. Custom Skills ---
# Use the @skill decorator to define specific high-level workflows.
# These can be triggered directly via 'lovelaice --skill hello'.
@config.skill
async def smalltalk(ctx: Context, engine: Engine):
    """
    A friendly smalltalk when the user just wants to chat.
    """
    msg = await engine.reply(ctx)
    ctx.append(msg)
