"""TUI input loop: submitting a message drives agent.chat and renders blocks."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from lovelaice.tui.app import LovelaiceApp


@pytest.mark.asyncio
async def test_submit_calls_agent_and_renders_user_block(workspace_dir: Path) -> None:
    fake_agent = MagicMock()
    fake_agent.chat = AsyncMock(return_value=MagicMock(content="ok"))
    fake_agent.messages = [MagicMock(usage=None)]

    app = LovelaiceApp(
        config_path=Path(".lovelaice.py"),
        model=None,
        _build_agent=lambda: fake_agent,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#input")
        await pilot.press("h", "e", "l", "l", "o")
        await pilot.press("enter")
        await pilot.pause()
        # Wait for the worker to finish.
        for _ in range(20):
            if not app.query_one("#input").disabled:
                break
            await pilot.pause()

        fake_agent.chat.assert_awaited_with("hello")
        transcript = app.query_one("#transcript")
        assert any(
            getattr(b, "role", None) == "user" and b.text == "hello"
            for b in transcript.blocks
        )
