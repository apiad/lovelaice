"""Textual app skeleton smoke tests, driven via App.run_test()."""
from __future__ import annotations

from pathlib import Path

import pytest

from lovelaice.tui.app import LovelaiceApp


@pytest.mark.asyncio
async def test_app_mounts_with_header_transcript_input_footer(workspace_dir: Path) -> None:
    """The app starts up and exposes the four core regions by id."""
    app = LovelaiceApp(
        config_path=Path(".lovelaice.py"),
        model=None,
        _build_agent=lambda: None,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.query_one("#header") is not None
        assert app.query_one("#transcript") is not None
        assert app.query_one("#input") is not None
        assert app.query_one("#footer") is not None


@pytest.mark.asyncio
async def test_app_quits_on_ctrl_d(workspace_dir: Path) -> None:
    app = LovelaiceApp(
        config_path=Path(".lovelaice.py"),
        model=None,
        _build_agent=lambda: None,
    )
    async with app.run_test() as pilot:
        await pilot.press("ctrl+d")
        await pilot.pause()
    # If we exited cleanly the context manager closes; no exception.
