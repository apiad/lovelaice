"""Textual full-screen TUI app for lovelaice. Single-pane layout:
header (model + cwd) / transcript (scrolling) / input / footer.

The app holds the agent instance built from the workspace's .lovelaice.py
and dispatches user input to it. Streaming hooks wire `on_token` and
`on_reasoning_token` into the active transcript block.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Input, Static

from .transcript import Transcript


class LovelaiceApp(App):
    """The lovelaice full-screen TUI."""

    CSS = """
    Screen { layout: vertical; }
    #header { dock: top; height: 1; background: $boost; color: $text; padding: 0 1; }
    #footer { dock: bottom; height: 1; background: $boost; color: $text-muted; padding: 0 1; }
    #input { dock: bottom; height: auto; }
    #transcript { height: 1fr; }
    """

    BINDINGS = [
        Binding("ctrl+d", "quit", "Quit", show=False),
        Binding("ctrl+c", "cancel_or_quit", "Cancel", show=True),
    ]

    def __init__(
        self,
        config_path: Path,
        model: Optional[str],
        _build_agent: Optional[Callable[..., Any]] = None,
    ) -> None:
        super().__init__()
        self._config_path = config_path
        self._model_arg = model
        self._build_agent = _build_agent
        self._agent: Any = None
        self._last_ctrl_c_t: float = 0.0
        self._cumulative_usage = {"prompt": 0, "completion": 0, "total": 0}
        self._available_models: list[str] = []
        self._active_model: Optional[str] = None
        self._current_turn: Any = None

    def compose(self) -> ComposeResult:
        yield Static(self._header_text(), id="header")
        yield Transcript(id="transcript")
        yield Input(placeholder="Ask lovelaice…", id="input")
        yield Static(self._footer_text(), id="footer")

    def _header_text(self) -> str:
        model = self._active_model or self._model_arg or "default"
        return f"Lovelaice · {model} · {os.getcwd()}"

    def _footer_text(self) -> str:
        return "Enter submit · Shift+Enter newline · Ctrl+C cancel · Ctrl+D exit · /help"

    async def on_mount(self) -> None:
        if self._build_agent is None:
            from ..config import load_agent_from_config
            cfg = load_agent_from_config(self._config_path)
            transcript = self.query_one("#transcript", Transcript)
            self._available_models = list(cfg.models.keys())
            self._active_model = self._model_arg or cfg.default_model
            self._agent = cfg.build(
                model=self._model_arg,
                on_token=transcript.on_reply_token,
                on_reasoning_token=transcript.on_reasoning_token,
            )
            # Refresh header now that we know the active model.
            self.query_one("#header", Static).update(self._header_text())
        else:
            self._agent = self._build_agent()

    async def on_input_submitted(self, event) -> None:
        """User pressed Enter in the input box."""
        text = event.value.strip()
        if not text:
            return
        input_widget = self.query_one("#input", Input)
        input_widget.value = ""

        if text.startswith("/"):
            from .slash import handle_slash
            await handle_slash(self, text)
            return

        transcript = self.query_one("#transcript", Transcript)
        transcript.add_user_message(text)
        input_widget.disabled = True
        self._current_turn = self.run_worker(self._run_turn(text), exclusive=True)

    async def _run_turn(self, prompt: str) -> None:
        """Drive one agent turn. Streaming hooks fire on the transcript."""
        transcript = self.query_one("#transcript", Transcript)

        def on_tool_call(result) -> None:
            res_text = "" if result.result is None else str(result.result)
            summary = res_text.splitlines()[0][:80] if res_text else ""
            transcript.add_tool_call(
                tool_name=result.tool,
                summary=summary,
                result=res_text,
                error=result.error,
            )

        try:
            self._agent._on_tool_call = on_tool_call
            await self._agent.chat(prompt)
            transcript.close_reply_block()
            usage = getattr(self._agent.messages[-1], "usage", None)
            if usage is not None:
                self._cumulative_usage["prompt"] += usage.prompt_tokens
                self._cumulative_usage["completion"] += usage.completion_tokens
                self._cumulative_usage["total"] += usage.total_tokens
        except Exception as e:
            transcript.add_error(f"{type(e).__name__}: {e}")
        finally:
            self.query_one("#input", Input).disabled = False

    async def action_cancel_or_quit(self) -> None:
        """Filled in by Task 16. For now, quit."""
        await self.action_quit()


async def run_tui(config_path: Path, *, model: Optional[str]) -> None:
    """Entrypoint called from cli.py."""
    app = LovelaiceApp(config_path=config_path, model=model)
    await app.run_async()
