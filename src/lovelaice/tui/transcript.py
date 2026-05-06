"""Scrolling transcript widget for the TUI. Renders an ordered list of blocks."""
from __future__ import annotations

from typing import Optional

from rich.console import Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from textual.containers import VerticalScroll
from textual.widgets import Static

from .blocks import (
    ErrorBlock, MessageBlock, ReplyBlock, ThinkingBlock, ToolCallBlock,
)


class Transcript(VerticalScroll):
    """Holds an ordered list of conversation blocks and renders them."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.blocks: list = []
        self._current_reply: Optional[ReplyBlock] = None
        self._current_thinking: Optional[ThinkingBlock] = None
        self._sink: Optional[Static] = None

    def on_mount(self) -> None:
        self._sink = Static("", expand=True)
        self.mount(self._sink)

    # --- public API used by the app -----------------------------------

    def add_user_message(self, text: str) -> None:
        self.blocks.append(MessageBlock(role="user", text=text))
        self._refresh()

    def open_thinking_block(self) -> ThinkingBlock:
        b = ThinkingBlock()
        self._current_thinking = b
        self.blocks.append(b)
        return b

    def close_thinking_block(self) -> None:
        if self._current_thinking is not None:
            self._current_thinking.finalize()
            self._current_thinking = None
            self._refresh()

    def open_reply_block(self) -> ReplyBlock:
        b = ReplyBlock()
        self._current_reply = b
        self.blocks.append(b)
        return b

    def close_reply_block(self) -> None:
        if self._current_reply is not None:
            self._current_reply.finalize()
            self._current_reply = None
            self._refresh()

    def add_tool_call(self, tool_name: str, summary: str, result: str = "", error: str | None = None) -> None:
        self.blocks.append(ToolCallBlock(tool_name=tool_name, summary=summary, result=result, error=error))
        self._refresh()

    def add_error(self, message: str) -> None:
        self.blocks.append(ErrorBlock(message=message))
        self._refresh()

    def clear_context_marker(self) -> None:
        self.blocks.append(MessageBlock(role="system", text="── context cleared ──"))
        self._refresh()

    # --- streaming hooks (called from LLM callbacks) ------------------

    def on_reply_token(self, token: str) -> None:
        if self._current_thinking is not None:
            self.close_thinking_block()
        if self._current_reply is None:
            self.open_reply_block()
        assert self._current_reply is not None
        self._current_reply.append(token)
        self._refresh()

    def on_reasoning_token(self, token: str) -> None:
        if self._current_thinking is None:
            self.open_thinking_block()
        assert self._current_thinking is not None
        self._current_thinking.append(token)
        self._refresh()

    # --- rendering ----------------------------------------------------

    def _render_block(self, block) -> Panel | Text:
        if isinstance(block, MessageBlock):
            if block.role == "user":
                return Panel(Text(block.text, style="bold green"), border_style="green", expand=False)
            return Text(block.text, style="dim")
        if isinstance(block, ReplyBlock):
            return Panel(
                Markdown(block.text or " "),
                title="[bold blue]Lovelaice[/]",
                border_style="blue",
                expand=False,
            )
        if isinstance(block, ThinkingBlock):
            body = (
                Markdown(block.text or " ")
                if not block.collapsed
                else Text("(thinking — click to expand)", style="dim italic")
            )
            return Panel(body, title="[dim italic]thinking[/]", border_style="bright_black", expand=False)
        if isinstance(block, ToolCallBlock):
            color = "red" if block.error else "yellow"
            head = f"{block.tool_name}: {block.summary}" + (f"  ✗ {block.error}" if block.error else "")
            return Text(head, style=color)
        if isinstance(block, ErrorBlock):
            return Panel(Text(block.message, style="bold red"), border_style="red", expand=False)
        return Text(repr(block))

    def _refresh(self) -> None:
        if self._sink is None:
            return
        group = Group(*[self._render_block(b) for b in self.blocks])
        self._sink.update(group)
        self.scroll_end(animate=False)
