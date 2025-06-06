from argo import ChatAgent, LLM, Context


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


class Lovelaice(ChatAgent):
    def __init__(self, llm: LLM):
        super().__init__(
            "Lovelaice",
            "A helpful AI agent that runs in the user terminal.",
            llm,
            system_prompt=SYSTEM_PROMPT)

        # register all skills
        self.skill(self.chat)

        # register all tools

    async def chat(self, ctx: Context):
        """
        Chat with Lovelaice. Use this skill for casual chat.
        """
        yield await ctx.reply()
