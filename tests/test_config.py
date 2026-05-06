"""Config extensions: name override, bash_timeout, mcp specs."""
from __future__ import annotations

import sys

import pytest

from lovelaice.config import Config

bash_module = sys.modules.setdefault(
    "lovelaice.tools.bash", __import__("lovelaice.tools.bash", fromlist=["_"])
)


def test_config_tool_accepts_name_override() -> None:
    cfg = Config(models={"default": {"model": "x"}}, prompt="x")

    async def list_(path: str = ".") -> list[str]:
        """List."""
        return []

    cfg.tool(list_, name="list")
    assert cfg.tools[0]._name_override == "list"
    assert cfg.tools[0]._target is list_


def test_config_bash_timeout_mutates_module() -> None:
    original = bash_module.BASH_TIMEOUT
    try:
        cfg = Config(models={"default": {"model": "x"}}, prompt="x", bash_timeout=7.5)
        cfg._apply_bash_timeout()
        assert bash_module.BASH_TIMEOUT == 7.5
    finally:
        bash_module.BASH_TIMEOUT = original


def test_config_mcp_stores_specs() -> None:
    cfg = Config(
        models={"default": {"model": "x"}},
        prompt="x",
        mcp=[{"name": "fs", "command": "echo", "args": []}],
    )
    assert cfg.mcp == [{"name": "fs", "command": "echo", "args": []}]


def test_config_default_mcp_is_empty() -> None:
    cfg = Config(models={"default": {"model": "x"}}, prompt="x")
    assert cfg.mcp == []
