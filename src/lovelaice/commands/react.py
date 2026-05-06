from lingo import Context, Engine, Message


REACT_HEADER = """
You are operating as an autonomous agent in a tool-use loop.

On each step you can either call one of the registered tools to make
progress on the user's task, or stop the loop and reply directly to
the user with the final answer.

Call tools whenever you need to read, modify, or inspect anything in
the environment. Stop only when you have everything you need to give
a complete answer. Do not narrate plans without acting on them.
""".strip()


DONE_INSTRUCTION = (
    "Has the user's most recent request been fully resolved by the work done so far? "
    "Answer True only if the next message to the user can be the final answer with "
    "no further tool calls. Answer False if there is still investigation, modification, "
    "or verification left to do."
)


async def react(context: Context, engine: Engine, *, max_steps: int = 20) -> None:
    """
    Generalist ReAct loop: decide-equip-invoke until the LLM signals done.

    Each iteration:
      1. Ask the LLM whether the user's request is fully resolved.
      2. If yes, exit the loop.
      3. Otherwise, equip a tool (LLM picks from the registered set),
         invoke it (LLM fills in parameters), and append the ToolResult
         as a `tool`-role message in the context.

    After the loop, ask the LLM for a final natural-language reply.
    """
    context.append(Message.system(REACT_HEADER))

    on_tool_call = getattr(engine, "_lovelaice_on_tool_call", None)

    for _ in range(max_steps):
        done = await engine.decide(context, DONE_INSTRUCTION)
        if done:
            break

        tool = await engine.equip(context)
        result = await engine.invoke(context, tool)
        if result.error:
            observation = f"[tool {result.tool} failed]\n{result.error}"
        else:
            observation = f"[tool {result.tool} result]\n{result.result}"
        context.append(Message.system(observation))

        if on_tool_call is not None:
            on_tool_call(result)

    final = await engine.reply(
        context,
        "Reply to the user now with a concise summary of what was done and the answer to their request.",
    )
    context.append(final)
