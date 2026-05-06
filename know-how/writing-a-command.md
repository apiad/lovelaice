# Writing a command

A command is an `async def(context, engine)` workflow registered with
`@config.command`. It runs as a `lingo` skill: the agent dispatches to
it on user input. The default `react` command (in
`src/lovelaice/commands/react.py`) is a good template.

## Building blocks

`engine` exposes:

- `engine.decide(context, prompt)` — yes/no decision.
- `engine.choose(context, options, prompt)` — pick from a list.
- `engine.equip(context)` — pick a tool from the registered set.
- `engine.invoke(context, tool)` — run the chosen tool with LLM-filled
  parameters.
- `engine.reply(context, *instructions)` — generate a final assistant
  message.
- `engine.create(context, model_cls, *instructions)` — structured
  output (Pydantic).

`context.append(message)` adds a message; `context.messages` is the
full transcript so far.

## Pattern: a planner-then-act command

```python
@config.command
async def plan_then_execute(context, engine):
    """Produce a step-by-step plan, then execute it."""
    plan = await engine.reply(context, "First, sketch a numbered plan. Do not act yet.")
    context.append(plan)
    # … iterate equip/invoke as in react …
    final = await engine.reply(context, "Summarize what was done.")
    context.append(final)
```

## Anti-patterns

- Calling `engine.act` — that does not exist on `Engine`. Use
  `equip(...)` then `invoke(...)`.
- Using `Message.tool(result.model_dump())` — `Message.tool` requires
  string content; use `Message.tool(result.model_dump_json())`.
- Adding side effects to `before` hooks that the model can see — they
  go into the system prompt and bloat context.
