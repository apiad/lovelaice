"""Shared fixtures for the lovelaice test suite."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def workspace_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A scratch directory with a stub .lovelaice.py, used as the cwd."""
    config = tmp_path / ".lovelaice.py"
    config.write_text(
        "from lovelaice import Config\n"
        "config = Config(models={'default': {'model': 'x'}}, prompt='x')\n"
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path
