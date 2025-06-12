from argo import ChatAgent, LLM, Context
from argo.llm import Message
from rich import get_console, print


SYSTEM_PROMPT = """
You are Lovelaice.

You are a smart, helpful AI agent that runs in the user terminal.
You can run bash commands, execute Python code, generate scripts, and
scaffold small projects.

You can also search the internet for questions of many kinds,
from trivia to programming to system engieering.
You can also answer questions about the user's files and code,
and manipulate the user filesytem, always with user confirmation.
"""


from argo.skills import MethodSkill, Skill
from argo.tools import MethodTool


class LovelaiceSkill(MethodSkill):
    async def execute(self, ctx: Context):
        print(f"[green]Executing skill [bold]{self.name}[/bold][/green]")
        await super().execute(ctx)


class LovelaiceTool(MethodTool):
    async def run(self, **kwargs):
        print(f"[yellow]Invoking [bold]{self.name}[/bold][/yellow]")
        return await super().run(**kwargs)


class LovelaiceContext(Context):
    async def engage(self, *instructions: str | Message) -> Skill:
        with get_console().status("Thinking...", spinner="dots"):
            return await super().engage(*instructions)


from lovelaice.skills import chat, linux, code
from lovelaice.tools import bash, python


class Lovelaice(ChatAgent):
    def __init__(self, llm: LLM):
        super().__init__(
            "Lovelaice",
            "A helpful AI agent that runs in the user terminal.",
            llm,
            system_prompt=SYSTEM_PROMPT,
            skill_cls=LovelaiceSkill,
            tool_cls=LovelaiceTool,
            context_cls=LovelaiceContext,
            skills=[chat, linux, code],
        )

        self.bash = self.tool(bash)
        self.python = self.tool(python)
