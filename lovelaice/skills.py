from argo import Context


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
