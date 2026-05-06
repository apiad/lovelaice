from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Callable, Coroutine, Optional

from lingo import LLM, Context, Engine

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


def load_agent_from_config(config_path: Path) -> Config:
    """
    Dynamically import the `.lovelaice.py` file at `config_path` and
    return its `config` object. The file is executed as a normal Python
    module, so any decorators registered on `config` take effect.
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


class Config:
    """
    Plugin registry for a Lovelaice agent.

    `.lovelaice.py` files instantiate one of these and decorate their
    custom tools and commands onto it. The CLI then calls `build()` to
    produce a configured `Lovelaice` instance.
    """

    def __init__(self, models: dict[str, dict], prompt: str):
        self.models = models
        self.default_model = next(iter(models))
        self.commands: list[Callable] = []
        self.tools: list[Callable] = []
        self.prompt = prompt
        self.agent: Lovelaice | None = None

    def command(self, func: Callable[[Context, Engine], Coroutine]):
        """Register a Python function as a top-level agent command (workflow)."""
        self.commands.append(func)
        return func

    def tool(self, func: Callable):
        """Register a Python function as a tool the agent can invoke."""
        self.tools.append(func)
        return func

    def build(self, model: str | None, on_token) -> Lovelaice:
        if self.agent is not None:
            raise RuntimeError("Config.build() already called once.")

        model = model or self.default_model
        self.agent = Lovelaice(
            llm=LLM(**self.models[model], on_token=on_token),
            prompt=self.prompt,
        )

        for tool in self.tools:
            self.agent.tool(tool)
        for cmd in self.commands:
            self.agent.skill(cmd)

        return self.agent
