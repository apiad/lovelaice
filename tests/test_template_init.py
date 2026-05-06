"""`lovelaice --init` writes a working .lovelaice.py."""
from __future__ import annotations

import inspect

from lovelaice import template


def test_template_renders_with_substitutions() -> None:
    src = inspect.getsource(template)
    assert "<default_model>" in src
    assert "<base_url>" in src
    assert "OPENROUTER_API_KEY" in src
    assert 'config.tool(list_, name="list")' in src
    assert "from lovelaice.tools import bash, read, write, edit, list_, glob, grep, fetch" in src
    assert "from lovelaice.commands import react" in src
