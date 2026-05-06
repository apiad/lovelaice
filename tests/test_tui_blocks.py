"""Block model tests."""
from __future__ import annotations

from lovelaice.tui.blocks import (
    ErrorBlock, MessageBlock, ReplyBlock, ThinkingBlock, ToolCallBlock,
)


def test_user_message_block_holds_text() -> None:
    b = MessageBlock(role="user", text="hello")
    assert b.role == "user"
    assert b.text == "hello"


def test_reply_block_appends_tokens() -> None:
    b = ReplyBlock()
    b.append("hello ")
    b.append("world")
    assert b.text == "hello world"


def test_thinking_block_collapsed_after_finalize() -> None:
    b = ThinkingBlock()
    b.append("thinking deeply")
    b.finalize()
    assert b.collapsed is True
    assert "thinking deeply" in b.text


def test_tool_call_block_summary_is_one_line() -> None:
    b = ToolCallBlock(tool_name="bash", summary="ran `ls`")
    assert b.summary == "ran `ls`"


def test_error_block_stores_message() -> None:
    b = ErrorBlock("LLM error: connection refused")
    assert "LLM error" in b.message
