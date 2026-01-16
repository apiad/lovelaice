from __future__ import annotations
from datetime import datetime
import getpass
import os

from lingo import LLM, Context, Engine, Lingo, Message

from .security import SecurityManager


class Lovelaice(Lingo):
    def __init__(self, llm: LLM, prompt: str, security: SecurityManager):
        super().__init__(
            name="Lovelaice",
            description="An AI engineering assistant.",
            llm=llm,
            system_prompt=prompt,
        )
        self.security = security

        self.registry.register(self.security)

        self.before(self.explain_context)

    async def explain_context(self, context: Context, engine: Engine):
        """
        Injects a detailed system message into the context before execution,
        outlining the current environment, tools, and security constraints.
        """
        # 1. Gather environment info
        cwd = os.getcwd()

        # 2. Format security constraints
        sec = self.security
        read_paths = "\n".join([f"  - {p}" for p in sec.read_paths]) or "  - None"
        write_paths = "\n".join([f"  - {p}" for p in sec.write_paths]) or "  - None"

        if sec.allow_execute is True:
            exec_info = "All shell commands are allowed (subject to user confirmation)."
        elif isinstance(sec.allow_execute, list):
            exec_info = f"Whitelisted commands: {', '.join(sec.allow_execute)}"
        else:
            exec_info = "Shell execution is strictly disabled."

        # 3. List registered Skills (complex workflows)
        # engine.skills is a dictionary mapping skill names to their functions
        skills_list = "\n".join(
            [f"  - {flow.name}: {flow.description}" for flow in self.skills]
        )

        # 4. List registered tools
        # engine.tools is a dictionary of Tool objects
        tools_list = "\n".join(
            [f"  - {tool.name}: {tool.description}" for tool in self.tools]
        )

        # Using getpass for a cleaner username fetch
        username = getpass.getuser()

        # 5. Construct the prompt
        status_prompt = f"""
# SYSTEM STATUS & CAPABILITIES

- **Current Date/Time:** {datetime.now().strftime("%A, %B %d, %Y - %H:%M:%S")}
- **Active User:** {username}

**Current Working Directory:** `{cwd}`

## 🛡️ Security Configuration
- **Read Access:** You can read from:
{read_paths}
- **Write Access:** You can write to:
{write_paths}
- **Execution:** {exec_info}

## 🧩 Registered Skills (High-Level Workflows)
Use these when the user requests a specific mode of operation:
{skills_list}

## 🔧 Registered Tools (Atomic Actions)
You can use these tools to interact with the system:
{tools_list}

**Operational Constraints:**
1. All destructive or external actions (write, delete, execute) require user confirmation (y/n/e).
2. If the user asks for 'explain' (e), provide a clear semantic explanation of the tool's intent.
3. Verify paths against allowed zones before attempting any action.
"""
        # Append as a system message so it's fresh in the context
        context.append(Message.system(status_prompt))
