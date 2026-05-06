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


async def react(context: Context, engine: Engine, *, max_steps: int = 20):
    """
    Generalist ReAct loop: think, act, observe, repeat until done.

    On each step the LLM decides whether the task is complete; if not,
    it picks a registered tool, generates parameters, and invokes it.
    The result is appended to the context as an observation. The loop
    exits when the LLM signals completion or the step budget is hit,
    after which a final natural-language reply is produced.

    Use this as the default agent behaviour when no more specific
    workflow has been registered.
    """
    context.append(Message.system(REACT_HEADER))

    for _ in range(max_steps):
        done = await engine.decide(context, DONE_INSTRUCTION)
        if done:
            break

        result = await engine.act(context)
        if result.error:
            context.append(
                Message.system(f"[tool {result.tool} failed] {result.error}")
            )
        else:
            context.append(
                Message.system(f"[tool {result.tool} result]\n{result.result}")
            )

    final = await engine.reply(
        context,
        "Reply to the user now with a concise summary of what was done and the answer to their request.",
    )
    context.append(final)
