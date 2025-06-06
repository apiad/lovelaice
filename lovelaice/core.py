import subprocess
from argo import ChatAgent, LLM, Context
from rich import print, get_console
from rich.prompt import Confirm


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


from argo.skills import MethodSkill
from argo.tools import MethodTool


class LovelaiceSkill(MethodSkill):
    async def execute(self, ctx: Context):
        print(f"[green]Executing skill [bold]{self.name}[/bold][/green]")
        async for m in super().execute(ctx):
            yield m


class LovelaiceTool(MethodTool):
    async def run(self, **kwargs):
        print(f"[yellow]Invoking [bold]{self.name}[/bold][/yellow]")
        return await super().run(**kwargs)


class Lovelaice(ChatAgent):
    def __init__(self, llm: LLM):
        super().__init__(
            "Lovelaice",
            "A helpful AI agent that runs in the user terminal.",
            llm,
            system_prompt=SYSTEM_PROMPT,
            skill_cls=LovelaiceSkill,
            tool_cls=LovelaiceTool,
            skills=[chat, linux],
        )

        self.bash = self.tool(bash)


async def chat(ctx: Context):
    """
    Chat with Lovelaice. Use this skill for casual chat.
    """
    yield await ctx.reply()


async def linux(ctx: Context):
    """
    Use the Linux terminal.

    This skill is useful when the user asks
    about the filesystem, install some program, etc.
    """
    ctx.add("Given the user query, generate a bash code to answer it.")

    result = await ctx.invoke(ctx.agent.bash, errors="handle")  # type: ignore
    print()

    ctx.add("After executing the bash script, you obtained the following result.")
    ctx.add(result)

    yield await ctx.reply("Reply concisely to the user.")


async def bash(script: str) -> str:
    """
    Run a bash script.

    Make sure the `script` argument is a
    Bash script, enclosed in triple backticks
    such as

    ```bash
    # the script here
    ```

    The script can have as many lines as necessary.
    """
    # strip backticks
    preamble = script.find("```bash")

    if preamble != -1:
        script = script[preamble + 7 :]

    postamble = script.rfind("```")

    if postamble != -1:
        script = script[:postamble]

    # inform the user

    print("Will run the following code:\n")

    if len(script.split("\n")) == 1:
        print("$ " + script)
    else:
        print(f"```bash\n{script}\n```")

    print()

    if Confirm.ask("Run the code?"):
        with get_console().status("Running code", spinner="dots"):
            result = subprocess.run(
                script, shell=True, capture_output=True, text=True, check=True
            )

        return result.stdout or "Script executed correctly."
    else:
        return "User aborted the script."
