"""Slash command dispatch. Filled in by Task 17."""
from __future__ import annotations


async def handle_slash(app, text: str) -> None:
    transcript = app.query_one("#transcript")
    transcript.add_error(f"unknown slash command: {text}")
