"""Cancellation: single Ctrl+C aborts the turn; double quits."""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from lovelaice.tui.app import LovelaiceApp


@pytest.mark.asyncio
async def test_single_ctrl_c_cancels_running_turn(workspace_dir: Path) -> None:
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def slow_chat(*a, **kw):
        started.set()
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            cancelled.set()
            raise

    fake_agent = MagicMock()
    fake_agent.chat = slow_chat
    fake_agent.messages = [MagicMock(usage=None)]

    app = LovelaiceApp(
        config_path=Path(".lovelaice.py"),
        model=None,
        _build_agent=lambda: fake_agent,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#input")
        await pilot.press("h", "i")
        await pilot.press("enter")
        await asyncio.wait_for(started.wait(), timeout=2.0)
        await pilot.press("ctrl+c")
        await asyncio.wait_for(cancelled.wait(), timeout=2.0)
        # The app should still be running (didn't quit).
        await pilot.pause()
