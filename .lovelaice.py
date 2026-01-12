import os
from datetime import date

from lingo import Context, Engine
from lovelaice import Lovelaice


# --- 1. Infrastructure ---
# The first model in this dictionary is the default for all operations.
# You can override this globally with the --model flag.
MODELS = {
    "flash": {
        "model": "gemini-1.5-flash",
        "api_key": os.getenv("GEMINI_API_KEY"),
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
    },
    "pro": {
        "model": "gemini-1.5-pro",
        "api_key": os.getenv("GEMINI_API_KEY"),
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
    },
}

# --- 2. Instantiate the agent
# You don't usually need to touch this, we are just building
# the Lovelaice instance passing all parameters
agent = Lovelaice(
    models=MODELS
)


# --- 3. Custom Tools ---
# Use the @tool decorator to give Lovelaice new atomic capabilities.
# These are automatically detected and available to the agent.
@agent.tool
def get_today() -> str:
    """
    Returns the current date in ISO format.
    Useful for context-aware tasks or file naming.
    """
    return date.today().isoformat()


# --- 4. Custom Skills ---
# Use the @skill decorator to define specific high-level workflows.
# These can be triggered directly via 'lovelaice --skill hello'.
@agent.skill
def greet(engine: Engine, ctx: Context):
    """
    A friendly greeting skill that identifies the current date.
    """
    today_date = get_today()
    print(f"🤖 Lovelaice: Hello! Today is {today_date}.")
