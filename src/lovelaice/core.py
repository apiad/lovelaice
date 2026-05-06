from __future__ import annotations
import getpass
import os
from datetime import datetime

from lingo import LLM, Context, Engine, Lingo, Message


class Lovelaice(Lingo):
    """
    The Lovelaice agent: a thin Lingo subclass that injects environment
    awareness into the system prompt before each turn.
    """

    def __init__(self, llm: LLM, prompt: str):
        super().__init__(
            name="Lovelaice",
            description="A local-first coding agent.",
            llm=llm,
            system_prompt=prompt,
        )
        self.before(self.explain_context)

    async def explain_context(self, context: Context, engine: Engine):
        """
        Prepends a fresh system message describing the current environment
        and the tools / commands the agent has access to. Re-emitted on
        every turn so the agent always sees up-to-date capabilities.
        """
        commands = "\n".join(
            f"  - {c.name}: {c.description}" for c in self.skills
        ) or "  - (none)"
        tools = "\n".join(
            f"  - {t.name}: {t.description}" for t in self.tools
        ) or "  - (none)"

        status = f"""
# Environment

- Time: {datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")}
- User: {getpass.getuser()}
- Workspace root (cwd): {os.getcwd()}

# Registered commands

{commands}

# Registered tools

{tools}

You operate in YOLO mode: tool calls execute immediately without
confirmation. Be deliberate about destructive actions (file writes,
shell commands that modify state) — read before you write, and
prefer surgical edits over full rewrites.
""".strip()

        context.append(Message.system(status))
