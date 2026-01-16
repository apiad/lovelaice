from lingo import Engine, Context, Message


async def chat(context: Context, engine: Engine):
    """
    A simple skill that just replies to the user in a conversation.

    Use this when the user is just having a casual conversation
    about any topic that doesn't require further actions on the agent.
    """
    # Simply request a reply from the LLM based on current context
    response = await engine.reply(context)

    # engine.chat (via LLM.chat) handles token streaming to the UI automatically
    # but we ensure the response is added to the conversation history
    context.append(response)


async def basic(context: Context, engine: Engine):
    """
    A single-turn tool execution skill.
    It selects the best tool for the task and invokes it once.

    Use this if the user requests some action in the filesystem,
    run a bash command, or otherwise any request that can solved with
    a single tool call.
    """
    # 1. Decide which tool is most appropriate for the last user message
    # engine.equip uses the LLM to choose from all registered tools
    tool = await engine.equip(context)

    # 2. Invoke the selected tool
    # This triggers parameter generation (LLM), UI confirmation,
    # and silent dependency injection (SecurityManager, LLM, etc.)
    result = await engine.invoke(context, tool)

    # 3. Add the result as an observation back to the context
    if result.error:
        context.append(Message.system(f"Tool {tool.name} failed: {result.error}"))
    else:
        context.append(Message.system(f"Tool {tool.name} result: {result.result}"))

    # 4. Final summary reply to the user explaining the result
    await chat(context, engine)
