"""Scrolling transcript widget for the TUI.

The block model and rendering land in Task 14; this stub provides just
enough surface for the app skeleton to mount.
"""
from __future__ import annotations

from textual.containers import VerticalScroll


class Transcript(VerticalScroll):
    """A vertically scrolling log of conversation blocks."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.blocks: list = []

    def on_reply_token(self, token: str) -> None:
        """Filled in by Task 14."""
        pass

    def on_reasoning_token(self, token: str) -> None:
        """Filled in by Task 14."""
        pass
