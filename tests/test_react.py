"""ReAct loop semantics, isolated from the LLM."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from lingo import Context, Message
from lingo.tools import ToolResult

from lovelaice.commands.react import react


@pytest.mark.asyncio
async def test_react_stops_when_decide_returns_true() -> None:
    """The loop calls engine.decide, gets True, skips equip/invoke, calls reply."""
    context = Context([Message.user("hi")])
    engine = MagicMock()
    engine.decide = AsyncMock(return_value=True)
    engine.equip = AsyncMock()
    engine.invoke = AsyncMock()
    engine.reply = AsyncMock(return_value=Message.assistant("done"))

    await react(context, engine)

    engine.decide.assert_awaited_once()
    engine.equip.assert_not_awaited()
    engine.invoke.assert_not_awaited()
    engine.reply.assert_awaited_once()
    assert context.messages[-1].content == "done"


@pytest.mark.asyncio
async def test_react_uses_equip_then_invoke_when_not_done() -> None:
    """If decide returns False, the loop calls equip() then invoke() and appends a tool message."""
    context = Context([Message.user("hi")])
    engine = MagicMock()
    fake_tool = MagicMock(name="bash")
    engine.decide = AsyncMock(side_effect=[False, True])
    engine.equip = AsyncMock(return_value=fake_tool)
    engine.invoke = AsyncMock(return_value=ToolResult(tool="bash", result="hello"))
    engine.reply = AsyncMock(return_value=Message.assistant("ok"))

    await react(context, engine)

    engine.equip.assert_awaited_once_with(context)
    engine.invoke.assert_awaited_once_with(context, fake_tool)
    assert any(m.role == "tool" for m in context.messages)


@pytest.mark.asyncio
async def test_react_handles_invoke_error() -> None:
    """If invoke returns a ToolResult with error, the loop continues with the error visible."""
    context = Context([Message.user("hi")])
    engine = MagicMock()
    fake_tool = MagicMock(name="bash")
    engine.decide = AsyncMock(side_effect=[False, True])
    engine.equip = AsyncMock(return_value=fake_tool)
    engine.invoke = AsyncMock(return_value=ToolResult(tool="bash", error="boom"))
    engine.reply = AsyncMock(return_value=Message.assistant("recovered"))

    await react(context, engine)

    tool_msgs = [m for m in context.messages if m.role == "tool"]
    assert len(tool_msgs) == 1
    assert "boom" in str(tool_msgs[0].content)
