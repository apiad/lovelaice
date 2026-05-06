"""The Lovelaice subclass injects an environment-status block each turn."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from lingo import Context

from lovelaice.core import Lovelaice


@pytest.mark.asyncio
async def test_explain_context_mentions_workspace_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    bot = Lovelaice.__new__(Lovelaice)
    bot.skills = []
    bot.tools = []

    ctx = Context([])
    engine = MagicMock()
    await bot.explain_context(ctx, engine)

    last = ctx.messages[-1]
    assert "Workspace root" in str(last.content)
    assert str(tmp_path) in str(last.content)


@pytest.mark.asyncio
async def test_explain_context_lists_mcp_tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    bot = Lovelaice.__new__(Lovelaice)
    bot.skills = []
    fake_tool = MagicMock(); fake_tool.name = "mcp:fs:read"; fake_tool.description = "read a file"
    bot.tools = [fake_tool]

    ctx = Context([])
    engine = MagicMock()
    await bot.explain_context(ctx, engine)

    last_text = str(ctx.messages[-1].content)
    assert "mcp:fs:read" in last_text
    assert "read a file" in last_text
