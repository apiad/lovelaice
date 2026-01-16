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

# You can give Lovelaice a custom prompt here.
# The exact list of capabilities, tools, and security options
# available are injected in runtime, so here you just need to
# explain high-level interaction rules.

PROMPT = f"""
You are Lovelaice, an AI engineering agent. You are empathetic, insightful,
and designed to assist with coding, debugging, documentation, systems engineering,
and any task performed via the CLI.

Be concise but helpful. If a task is ambiguous, ask for clarification instead of guessing.
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

# Bash-related tools
from lovelaice.tools.shell import execute_command

config.tool(execute_command)

# --- 4. Register common skills ---

from lovelaice.skills.basic import chat, basic

# Register skills with the agent
config.skill(chat)
config.skill(basic)

# --- 5. Custom tools and skills

# Use @config.tool or @config.skill to add your own tools and skills here.

# Refer to the docs for help <https://apiad.net/lovelaice>
