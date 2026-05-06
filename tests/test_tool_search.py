"""Tests for glob and grep."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_glob_matches_recursive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lovelaice.tools import glob as glob_tool

    monkeypatch.chdir(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("")
    (tmp_path / "src" / "b.txt").write_text("")
    (tmp_path / "README.md").write_text("")

    py_files = await glob_tool("**/*.py")
    assert "src/a.py" in py_files
    assert "src/b.txt" not in py_files


@pytest.mark.asyncio
async def test_glob_respects_gitignore(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lovelaice.tools import glob as glob_tool

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".gitignore").write_text("ignored/\n*.log\n")
    (tmp_path / "ignored").mkdir()
    (tmp_path / "ignored" / "x.py").write_text("")
    (tmp_path / "kept.py").write_text("")
    (tmp_path / "noisy.log").write_text("")

    files = await glob_tool("**/*")
    assert "kept.py" in files
    assert "ignored/x.py" not in files
    assert "noisy.log" not in files


@pytest.mark.asyncio
async def test_grep_returns_path_line_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lovelaice.tools import grep

    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.txt").write_text("foo\nbar\nbaz\n")
    (tmp_path / "b.txt").write_text("nothing\nfoo\n")

    out = await grep("foo")
    assert "a.txt:1:foo" in out
    assert "b.txt:2:foo" in out


@pytest.mark.asyncio
async def test_grep_caps_at_200(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lovelaice.tools import grep

    monkeypatch.chdir(tmp_path)
    (tmp_path / "many.txt").write_text("\n".join(["match"] * 500))

    out = await grep("match")
    assert "truncated at 200 hits" in out


@pytest.mark.asyncio
async def test_grep_skips_binary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lovelaice.tools import grep

    monkeypatch.chdir(tmp_path)
    (tmp_path / "bin").write_bytes(b"\x00\x01match\x02")
    (tmp_path / "txt").write_text("match\n")

    out = await grep("match")
    assert "bin:" not in out
    assert "txt:1:match" in out
