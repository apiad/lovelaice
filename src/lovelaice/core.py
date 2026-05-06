from __future__ import annotations

import getpass
import os
from datetime import datetime

from lingo import LLM, Context, Engine, Lingo, Message
from lingo.engine import Engine as _Engine


class Lovelaice(Lingo):
    """
    The Lovelaice agent: a thin Lingo subclass that injects environment
    awareness into the system prompt before each turn and forwards a
    tool-call hook through to the running Engine.
    """

    def __init__(self, llm: LLM, prompt: str):
        super().__init__(
            name="Lovelaice",
            description="A local-first coding agent.",
            llm=llm,
            system_prompt=prompt,
        )
        self.before(self.explain_context)
        # Set by the host (TUI / oneshot) before chat() to receive tool
        # observations. None → no hook fires.
        self._on_tool_call = None

    async def explain_context(self, context: Context, engine: Engine):
        """Prepend a fresh system message describing the current environment."""
        commands = "\n".join(f"  - {c.name}: {c.description}" for c in self.skills) or "  - (none)"
        tools = "\n".join(f"  - {t.name}: {t.description}" for t in self.tools) or "  - (none)"

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

    async def chat(self, msg: str) -> Message:
        """Same as Lingo.chat() but attaches `_lovelaice_on_tool_call` to the engine."""
        self.messages.append(Message.user(msg))
        context = Context(list(self.messages))
        engine = _Engine(self.llm, self.tools)
        engine._lovelaice_on_tool_call = self._on_tool_call
        flow = self._build_flow()
        await flow.execute(context, engine)
        for m in context.messages[len(self.messages):]:
            self.messages.append(m)
        return self.messages[-1]
