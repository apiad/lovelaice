"""Slash command dispatch for the TUI."""
from __future__ import annotations

import os


HELP_TEXT = """
Slash commands:
  /help               show this help
  /model              list configured models (current is starred)
  /model <alias>      switch active model for next turn
  /clear              wipe in-memory conversation context
  /cost               show cumulative token usage since launch
  /cwd                print the workspace root
  /exit, /quit        exit the app

Keys:
  Enter               submit
  Shift+Enter / Ctrl+J  newline
  Ctrl+C              cancel current turn (twice → quit)
  Ctrl+D              quit
""".strip()


async def handle_slash(app, text: str) -> None:
    transcript = app.query_one("#transcript")
    parts = text.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) == 2 else None

    if cmd == "/help":
        transcript.add_user_message(HELP_TEXT)
        return

    if cmd == "/cwd":
        transcript.add_user_message(os.getcwd())
        return

    if cmd in ("/exit", "/quit"):
        await app.action_quit()
        return

    if cmd == "/clear":
        if app._agent is not None:
            app._agent.messages = []
        transcript.clear_context_marker()
        return

    if cmd == "/cost":
        usage = getattr(app, "_cumulative_usage", None)
        if not usage or usage.get("total", 0) == 0:
            transcript.add_user_message("No usage recorded yet.")
        else:
            transcript.add_user_message(
                f"prompt_tokens={usage['prompt']}  "
                f"completion_tokens={usage['completion']}  "
                f"total={usage['total']}"
            )
        return

    if cmd == "/model":
        from textual.widgets import Static
        models = getattr(app, "_available_models", None) or []
        current = getattr(app, "_active_model", None)
        if not arg:
            if not models:
                transcript.add_user_message("(no models configured)")
                return
            lines = [f"  {'* ' if m == current else '  '}{m}" for m in models]
            transcript.add_user_message("Models:\n" + "\n".join(lines))
            return
        if models and arg not in models:
            transcript.add_error(f"unknown model alias: {arg!r}")
            return
        app._active_model = arg
        app.query_one("#header", Static).update(app._header_text())
        transcript.add_user_message(f"switched to {arg} for next turn")
        return

    transcript.add_error(f"unknown slash command: {cmd}")
