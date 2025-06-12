from argo import Context


async def chat(ctx: Context):
    """
    Chat with Lovelaice. Use this skill for casual chat.
    """
    await ctx.reply()


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

    await ctx.reply("Reply concisely to the user.")


async def code(ctx: Context):
    """
    Reply to a math or coding question by running Python code.

    This skill is useful when the user has a math or code question
    that can be solved by running basic Python code.
    """
    ctx.add("Given the user query, generate a Python code to answer it.")

    result = await ctx.invoke(ctx.agent.python, errors="handle")  # type: ignore
    print()

    ctx.add("After executing the Python script, you obtained the following result.")
    ctx.add(result)

    await ctx.reply("Reply concisely to the user.")
