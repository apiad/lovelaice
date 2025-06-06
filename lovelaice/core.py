import subprocess
from argo import ChatAgent, LLM, Context
from rich import print
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


class Lovelaice(ChatAgent):
    def __init__(self, llm: LLM):
        super().__init__(
            "Lovelaice",
            "A helpful AI agent that runs in the user terminal.",
            llm,
            system_prompt=SYSTEM_PROMPT)

        # register all skills
        self.skill(chat)
        self.skill(bash)

        # register all tools
        self.run_bash = self.tool(run_bash)


async def chat(ctx: Context):
    """
    Chat with Lovelaice. Use this skill for casual chat.
    """
    yield await ctx.reply()


async def bash(ctx: Context):
    """
    Use bash code.

    This skill is useful when the user asks
    about the filesystem, install some program, etc.
    """
    ctx.add("Given the user query, generate a bash code to answer it.")
    result = await ctx.invoke(ctx.agent.run_bash) # type: ignore
    print()

    ctx.add("After executing the bash script, you obtained the following result.")
    ctx.add(result)

    yield await ctx.reply("Reply concisely to the user.")


async def run_bash(script: str) -> str:
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
        script = script[preamble + 7:]

    postamble = script.rfind("```")

    if postamble != -1:
        script = script[:postamble]

    # inform the user

    print("Will run the following code:\n")
    print(script)
    print()

    if Confirm.ask("Run the code?"):
        result = subprocess.run(script, shell=True, capture_output=True, text=True)
        if result:
            return result.stdout
        else:
            return "Script executed correctly."
    else:
        return "User aborted the script."
