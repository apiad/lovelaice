from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional

from lingo import Context, Engine

from .core import Lovelaice


def find_config_file(start_path: Path = Path(".")) -> Optional[Path]:
    """
    Walk upwards from `start_path` looking for a `.lovelaice.py` config
    file. Returns the first match, or None if none is found before the
    filesystem root.
    """
    current = start_path.resolve()
    while True:
        config_path = current / ".lovelaice.py"
        if config_path.exists():
            return config_path
        if current == current.parent:
            return None
        current = current.parent


def load_agent_from_config(config_path: Path) -> "Config":
    """
    Dynamically import the `.lovelaice.py` file at `config_path` and
    return its `config` object.
    """
    module_name = "lovelaice.local_config"

    spec = importlib.util.spec_from_file_location(module_name, config_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for {config_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception as e:
        raise RuntimeError(f"Error executing config at {config_path}: {e}")

    if not hasattr(module, "config"):
        raise AttributeError(
            f"The config at {config_path} must define a `config` variable."
        )

    return module.config


@dataclass
class _ToolEntry:
    """Internal: tool function + optional display-name override."""
    _target: Callable
    _name_override: str | None = None


class Config:
    """
    Plugin registry for a Lovelaice agent.

    `.lovelaice.py` files instantiate one of these and decorate their
    custom tools and commands onto it. The CLI then calls `build()` to
    produce a configured `Lovelaice` instance.
    """

    def __init__(
        self,
        models: dict[str, dict],
        prompt: str,
        *,
        bash_timeout: float | None = None,
        mcp: list[dict[str, Any]] | None = None,
    ):
        self.models = models
        self.default_model = next(iter(models))
        self.prompt = prompt
        self.bash_timeout = bash_timeout
        self.mcp: list[dict[str, Any]] = list(mcp or [])
        self.commands: list[Callable] = []
        self.tools: list[_ToolEntry] = []
        self.agent: Lovelaice | None = None

    def command(self, func: Callable[[Context, Engine], Coroutine]):
        """Register a Python function as a top-level agent command (workflow)."""
        self.commands.append(func)
        return func

    def tool(self, func: Callable, *, name: str | None = None):
        """
        Register a Python function as a tool. Optionally override the
        display name (e.g., to register `list_` as `"list"`).
        """
        self.tools.append(_ToolEntry(_target=func, _name_override=name))
        return func

    def _apply_bash_timeout(self) -> None:
        """Mutate the BASH_TIMEOUT module global if configured."""
        if self.bash_timeout is None:
            return
        # `from .tools import bash` would shadow with the function;
        # import the submodule directly via importlib.
        from importlib import import_module
        bash_mod = import_module("lovelaice.tools.bash")
        bash_mod.BASH_TIMEOUT = self.bash_timeout

    def build(self, model: str | None, on_token, on_reasoning_token=None) -> Lovelaice:
        if self.agent is not None:
            raise RuntimeError("Config.build() already called once.")

        self._apply_bash_timeout()

        model = model or self.default_model
        model_kwargs = dict(self.models[model])
        thinking = model_kwargs.pop("thinking", None)

        from .thinking import build_llm
        llm = build_llm(
            model_kwargs=model_kwargs,
            thinking=thinking,
            on_token=on_token,
            on_reasoning_token=on_reasoning_token,
        )

        self.agent = Lovelaice(llm=llm, prompt=self.prompt)

        # Register decorated tools, applying name overrides.
        for entry in self.tools:
            t = self.agent.tool(entry._target)
            if entry._name_override is not None:
                t._name = entry._name_override

        # Register MCP-loaded tools.
        if self.mcp:
            from .mcp import register_mcp_tools
            register_mcp_tools(self.agent, self.mcp)

        for cmd in self.commands:
            self.agent.skill(cmd)

        return self.agent
