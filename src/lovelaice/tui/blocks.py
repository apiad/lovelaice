"""Conversation blocks rendered in the transcript."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class MessageBlock:
    """A user, assistant, or system message rendered in plain text."""
    role: Literal["user", "assistant", "system"]
    text: str = ""

    def append(self, token: str) -> None:
        self.text += token


@dataclass
class ReplyBlock:
    """Streaming agent reply, rendered as a bordered Markdown panel."""
    text: str = ""
    finalized: bool = False

    def append(self, token: str) -> None:
        self.text += token

    def finalize(self) -> None:
        self.finalized = True


@dataclass
class ThinkingBlock:
    """Reasoning tokens, dim/italic, collapsible."""
    text: str = ""
    collapsed: bool = False

    def append(self, token: str) -> None:
        self.text += token

    def finalize(self) -> None:
        self.collapsed = True


@dataclass
class ToolCallBlock:
    """One tool invocation. Summary line stays visible; result body collapses."""
    tool_name: str
    summary: str = ""
    result: str = ""
    error: str | None = None
    collapsed: bool = True


@dataclass
class ErrorBlock:
    """A red banner for LLM transport errors."""
    message: str
