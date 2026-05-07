"""Translate the user-facing ``thinking=`` knob into an OpenRouter
``reasoning`` body kwarg, and instantiate `lingo.LLM` accordingly.

As of `lingo-ai>=1.5.0`, reasoning passthrough lives in `lingo.LLM`
itself: it accepts an `on_reasoning_token` callback and a `reasoning`
body kwarg that's injected only on the streaming `chat()` path. So this
module is now just a thin translation layer over the user's config.
"""
from __future__ import annotations

from typing import Any, Callable

from lingo import LLM


def _resolve_reasoning_kwargs(thinking: str | int | None) -> dict[str, Any] | None:
    """Translate the user-facing ``thinking=`` knob into OpenRouter's body kwarg."""
    if thinking is None:
        return None
    if isinstance(thinking, int):
        return {"max_tokens": thinking}
    if thinking in ("low", "medium", "high"):
        return {"effort": thinking}
    raise ValueError(
        f"thinking must be 'low'|'medium'|'high', an int (token budget), or None; got {thinking!r}"
    )


def build_llm(
    *,
    model_kwargs: dict[str, Any],
    thinking: str | int | None,
    on_token: Callable[[str], Any] | None,
    on_reasoning_token: Callable[[str], Any] | None,
) -> LLM:
    """Build a `lingo.LLM`, attaching reasoning passthrough only when
    `thinking` is set and the configured base URL is OpenRouter.

    The thinking knob is silently ignored on non-OpenRouter base URLs —
    we don't translate per provider. If a future provider needs the same
    body kwarg, extend the gate here.
    """
    base_url = model_kwargs.get("base_url", "") or ""
    use_reasoning = thinking is not None and "openrouter.ai" in base_url
    reasoning = _resolve_reasoning_kwargs(thinking) if use_reasoning else None

    return LLM(
        on_token=on_token,
        on_reasoning_token=on_reasoning_token if use_reasoning else None,
        reasoning=reasoning,
        **model_kwargs,
    )
