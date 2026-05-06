# Writing a tool

A tool is an async (or sync) Python function decorated with
`@config.tool`. The function's docstring becomes the description the
LLM sees; its annotated parameters become the parameter schema.

## Conventions

- **Async** preferred. Sync functions are auto-wrapped, but the agent
  loop runs async, so async is more direct.
- **Docstring is the prompt.** The LLM picks tools by reading the
  docstring; write it as if you are explaining to the model when to
  use this tool, not to a human reading source.
- **Return text.** Tool results are stringified and concatenated into
  the context as `tool`-role messages. Return a string (or a value
  that stringifies usefully); avoid huge blobs.
- **Workspace-rooted paths.** Cwd is the workspace root (lovelaice
  `chdir`s on startup); relative paths are correct.
- **Display-name override.** Use `config.tool(my_func, name="x")` if
  the function name conflicts with a Python builtin (e.g., `list`).
- **Errors.** Raise normally. The loop catches exceptions and feeds
  them back as a `tool failed` observation.

## Example

```python
@config.tool
async def search_notes(query: str) -> str:
    """Search the user's notes (Obsidian vault) for `query`. Returns
    matching note paths and surrounding context, one match per line."""
    ...
```
