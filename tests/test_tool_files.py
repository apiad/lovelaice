"""Tests for the file tools."""
from __future__ import annotations

from pathlib import Path

import pytest

from lovelaice.tools import edit, list_, read, write


@pytest.mark.asyncio
async def test_list_underscore_returns_sorted_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "b").write_text("")
    (tmp_path / "a").write_text("")
    assert await list_() == ["a", "b"]


@pytest.mark.asyncio
async def test_list_underscore_explicit_path(tmp_path: Path) -> None:
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "x").write_text("")
    assert await list_(str(sub)) == ["x"]


@pytest.mark.asyncio
async def test_read_write_edit_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "f.txt"
    await write(str(p), "hello world")
    assert await read(str(p)) == "hello world"
    await edit(str(p), "world", "lovelaice")
    assert await read(str(p)) == "hello lovelaice"
