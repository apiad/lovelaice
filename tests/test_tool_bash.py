"""Tests for the bash tool."""
from __future__ import annotations

import sys

import pytest

# `from .bash import bash` in tools/__init__.py shadows the submodule
# attribute, so `import lovelaice.tools.bash as bash_module` returns the
# function. Use sys.modules to grab the module itself.
bash_module = sys.modules.setdefault(
    "lovelaice.tools.bash", __import__("lovelaice.tools.bash", fromlist=["_"])
)


@pytest.mark.asyncio
async def test_bash_returns_combined_stdout_stderr() -> None:
    out = await bash_module.bash("echo hi; echo err 1>&2")
    assert "hi" in out
    assert "err" in out


@pytest.mark.asyncio
async def test_bash_times_out() -> None:
    """A long-running command honors the timeout knob."""
    original = bash_module.BASH_TIMEOUT
    bash_module.BASH_TIMEOUT = 0.5
    try:
        with pytest.raises(TimeoutError) as ei:
            await bash_module.bash("sleep 5")
        assert "timed out" in str(ei.value).lower()
    finally:
        bash_module.BASH_TIMEOUT = original


@pytest.mark.asyncio
async def test_bash_nonzero_exit_returns_output() -> None:
    """A nonzero exit doesn't raise; the output (incl. stderr) is returned."""
    out = await bash_module.bash("false; echo done")
    assert "done" in out
