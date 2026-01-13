from __future__ import annotations

import sys
import importlib.util
from pathlib import Path
from typing import Callable, Coroutine, Optional, Any

from lingo import LLM, Context, Engine

from lovelaice.core import Lovelaice


def find_config_file(start_path: Path = Path(".")) -> Optional[Path]:
    """
    Recursively searches upwards for a .lovelaice.py file.
    Stops at the first one found or at the root directory.
    """
    current = start_path.resolve()

    while True:
        config_path = current / ".lovelaice.py"

        if config_path.exists():
            return config_path

        # Stop if we reach the root
        if current == current.parent:
            break

        current = current.parent

    return None


def load_agent_from_config(config_path: Path) -> Config:
    """
    Dynamically imports the .lovelaice.py file and retrieves
    the 'agent' variable.
    """
    module_name = "lovelaice.local_config"

    # Standard Python dynamic import boilerplate
    spec = importlib.util.spec_from_file_location(module_name, config_path)

    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for {config_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception as e:
        raise RuntimeError(f"Error executing config at {config_path}: {e}")

    # Extract the 'agent' instance as defined in your template
    if not hasattr(module, "config"):
        raise AttributeError(
            f"The config at {config_path} must define a 'config' variable."
        )

    return module.config


class Config:
    def __init__(self, models, prompt):
        self.models = models
        self.default_model = list(models)[0]
        self.skills = []
        self.tools = []
        self.prompt = prompt

    def register_skill(self, func: Callable[[Context, Engine], Coroutine]):
        self.skills.append(func)

    def register_tool(self, func: Callable):
        self.tools.append(func)

    def build(self, model: str | None, on_token=None) -> Lovelaice:
        if model is None:
            model = self.default_model

        agent = Lovelaice(
            llm=LLM(**self.models[model], on_token=on_token), prompt=self.prompt
        )

        # Register tools
        for tool in self.tools:
            agent.tool(tool)

        # Register skills
        for skill in self.skills:
            agent.skill(skill)

        return agent
