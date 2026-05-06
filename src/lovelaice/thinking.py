"""OpenRouter reasoning passthrough — extends lingo's LLM to capture
`delta.reasoning` chunks and forward them to a separate callback.

We subclass because `lingo.LLM.chat()` reads only `delta.content` and
silently drops everything else; without subclassing, reasoning tokens
would never reach the UI.

Set ``LOVELAICE_DEBUG_STREAM=1`` to dump every streamed chunk to stderr
— useful when a provider returns reasoning under an unexpected field
or doesn't stream it at all.
"""
from __future__ import annotations

import inspect
import os
import sys
from typing import Any, Callable

from lingo import LLM, Message
from lingo.llm import Usage


def _resolve_reasoning_kwargs(thinking: str | int | None) -> dict[str, Any]:
    """Translate the user-facing `thinking=` knob into OpenRouter's body kwarg."""
    if thinking is None:
        return {}
    if isinstance(thinking, int):
        return {"reasoning": {"max_tokens": thinking}}
    if thinking in ("low", "medium", "high"):
        return {"reasoning": {"effort": thinking}}
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
    """
    Return a plain `lingo.LLM` when thinking is not requested, or a
    `ThinkingLLM` when it is. The thinking knob is silently ignored on
    non-OpenRouter base URLs (we don't translate per provider).
    """
    base_url = model_kwargs.get("base_url", "") or ""
    if thinking is None or "openrouter.ai" not in base_url:
        return LLM(on_token=on_token, **model_kwargs)
    extra = _resolve_reasoning_kwargs(thinking)
    return ThinkingLLM(
        on_token=on_token,
        on_reasoning_token=on_reasoning_token,
        **{**model_kwargs, **extra},
    )


class ThinkingLLM(LLM):
    """A `lingo.LLM` that also forwards `delta.reasoning` chunks.

    The OpenRouter ``reasoning`` body kwarg only applies to the streaming
    chat-completions path. Lingo's structured-output helpers (decide /
    choose / equip / invoke) call ``client.chat.completions.parse()``,
    which rejects ``reasoning`` as an unknown kwarg. So we keep the
    reasoning request out of ``extra_kwargs`` and inject it only inside
    our overridden ``chat()``.
    """

    def __init__(
        self,
        *args,
        on_reasoning_token: Callable[[str], Any] | None = None,
        reasoning: dict[str, Any] | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._on_reasoning_token = on_reasoning_token
        self._reasoning = reasoning

    async def on_reasoning_token(self, token: str) -> None:
        if self._on_reasoning_token is None:
            return
        resp = self._on_reasoning_token(token)
        if inspect.iscoroutine(resp):
            await resp

    async def chat(self, messages: list[Message], **kwargs) -> Message:
        """Same as lingo.LLM.chat(), but also routes reasoning deltas to a separate sink.

        Reasoning is read from any of these fields, in priority order:
        ``delta.reasoning`` (OpenRouter unified, OpenAI o-series),
        ``delta.reasoning_content`` (some Anthropic/DeepSeek paths), or
        ``delta.thoughts`` (some Gemini paths). The first non-empty one
        wins per chunk.
        """
        debug = bool(os.environ.get("LOVELAICE_DEBUG_STREAM"))
        content_chunks: list[str] = []
        usage: Usage | None = None
        api_messages = [msg.model_dump() for msg in messages]

        call_kwargs = {**self.extra_kwargs, **kwargs}
        if self._reasoning is not None:
            call_kwargs["reasoning"] = self._reasoning

        async for chunk in await self.client.chat.completions.create(
            model=self.model,
            messages=api_messages,
            stream=True,
            stream_options=dict(include_usage=True),
            **call_kwargs,
        ):
            if debug:
                print(f"[lovelaice-debug] chunk: {chunk}", file=sys.stderr, flush=True)

            if getattr(chunk, "usage", None):
                usage = Usage(
                    prompt_tokens=chunk.usage.prompt_tokens,
                    completion_tokens=chunk.usage.completion_tokens,
                    total_tokens=chunk.usage.total_tokens,
                )

            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            reasoning = _read_reasoning(delta)
            if reasoning:
                await self.on_reasoning_token(reasoning)

            content = getattr(delta, "content", None)
            if content:
                await self.on_token(content)
                content_chunks.append(content)

        result = Message.assistant("".join(content_chunks), usage=usage)
        await self.on_message(result)
        return result


def _read_reasoning(delta: Any) -> str | None:
    """Pull a streamed reasoning fragment from a delta, handling provider variance.

    OpenAI SDK preserves unknown fields via ``model_extra``; we check both
    the typed attribute path and the extras dict so we catch fields the
    SDK didn't model directly.
    """
    for name in ("reasoning", "reasoning_content", "thoughts"):
        value = getattr(delta, name, None)
        if value:
            return value
    extra = getattr(delta, "model_extra", None) or {}
    for name in ("reasoning", "reasoning_content", "thoughts"):
        value = extra.get(name)
        if value:
            return value
    return None
