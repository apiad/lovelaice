"""Slash command tests."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from lovelaice.tui.app import LovelaiceApp


@pytest.mark.asyncio
async def test_slash_cwd_shows_workspace_root(workspace_dir: Path) -> None:
    fake_agent = MagicMock()
    app = LovelaiceApp(
        config_path=Path(".lovelaice.py"),
        model=None,
        _build_agent=lambda: fake_agent,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#input")
        for ch in "/cwd":
            await pilot.press(ch if ch != "/" else "slash")
        await pilot.press("enter")
        await pilot.pause()
        transcript = app.query_one("#transcript")
        text_blob = "\n".join(
            getattr(b, "text", getattr(b, "message", ""))
            for b in transcript.blocks
        )
        assert str(workspace_dir) in text_blob


@pytest.mark.asyncio
async def test_slash_clear_resets_messages(workspace_dir: Path) -> None:
    fake_agent = MagicMock()
    fake_agent.messages = ["a", "b"]
    app = LovelaiceApp(
        config_path=Path(".lovelaice.py"),
        model=None,
        _build_agent=lambda: fake_agent,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#input")
        for ch in "/clear":
            await pilot.press(ch if ch != "/" else "slash")
        await pilot.press("enter")
        await pilot.pause()
        assert fake_agent.messages == []


@pytest.mark.asyncio
async def test_slash_exit_quits(workspace_dir: Path) -> None:
    fake_agent = MagicMock()
    app = LovelaiceApp(
        config_path=Path(".lovelaice.py"),
        model=None,
        _build_agent=lambda: fake_agent,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#input")
        for ch in "/exit":
            await pilot.press(ch if ch != "/" else "slash")
        await pilot.press("enter")
        await pilot.pause()
    # Run-test context exits on quit; reaching here means it quit cleanly.
