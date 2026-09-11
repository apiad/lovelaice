"""System-prompt assembler — three blocks in fixed order: base + tools_summary + env.

Composition order is for cache reuse (stable prefix, ephemeral suffix).
Composed once at session start in VS1; no dynamic prompt providers yet.
"""
from datetime import date as _date
from lovelaice.agent.tools import ToolRegistry


def assemble_system_prompt(
    *,
    base: str,
    tools: ToolRegistry,
    cwd: str,
    today: str | None = None,
    list_tools: bool = True,
) -> str:
    """Assemble the system prompt from three blocks (base + tools + env).

    Args:
        base: User-provided base instructions (from AgentConfig.system_prompt).
        tools: ToolRegistry whose tool descriptions are listed in the prompt.
        cwd: Current working directory, shown in the environment block.
        today: Optional ISO date string; defaults to date.today().isoformat().
        list_tools: List each tool as a one-liner in the prompt. Default True.
            A model using native function-calling already receives the tool
            list in the API `tools=` array, so this block restates it — and
            when the caller has truncated descriptions to one line, it is
            restated verbatim. Turn it off to stop paying for the same text
            twice per turn.

    Returns:
        The assembled system prompt with trailing newline.
    """
    parts: list[str] = [base.rstrip()]

    tool_list = tools.all() if list_tools else []
    if tool_list:
        lines = ["Available tools:"]
        for at in tool_list:
            desc = at.description.strip().splitlines()[0] if at.description else ""
            params = at.inner.parameters()
            sig = ", ".join(
                f"{n}: {getattr(t, '__name__', 'Any')}"
                for n, t in params.items()
            )
            lines.append(f"- {at.name}({sig}) — {desc}")
        parts.append("\n".join(lines))

    today_str = today or _date.today().isoformat()
    parts.append(f"Current date: {today_str}\nWorking directory: {cwd}")

    return "\n\n".join(parts) + "\n"
