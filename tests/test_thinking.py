"""Thinking mode: OpenRouter `reasoning` request injection + delta.reasoning streaming."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from types import SimpleNamespace

from lovelaice.thinking import ThinkingLLM, _read_reasoning, _resolve_reasoning_kwargs, build_llm


def test_read_reasoning_prefers_reasoning_field() -> None:
    delta = SimpleNamespace(reasoning="A", reasoning_content="B", thoughts="C")
    assert _read_reasoning(delta) == "A"


def test_read_reasoning_falls_back_to_reasoning_content() -> None:
    delta = SimpleNamespace(reasoning=None, reasoning_content="B", thoughts="C")
    assert _read_reasoning(delta) == "B"


def test_read_reasoning_falls_back_to_thoughts() -> None:
    delta = SimpleNamespace(reasoning=None, reasoning_content=None, thoughts="C")
    assert _read_reasoning(delta) == "C"


def test_read_reasoning_returns_none_when_absent() -> None:
    delta = SimpleNamespace()
    assert _read_reasoning(delta) is None


def test_read_reasoning_reads_from_model_extra() -> None:
    """OpenAI SDK preserves unknown fields in `model_extra` for some shapes."""
    delta = SimpleNamespace(reasoning=None, model_extra={"reasoning": "from extras"})
    assert _read_reasoning(delta) == "from extras"


def test_resolve_reasoning_kwargs_for_effort_levels() -> None:
    assert _resolve_reasoning_kwargs("low") == {"reasoning": {"effort": "low"}}
    assert _resolve_reasoning_kwargs("medium") == {"reasoning": {"effort": "medium"}}
    assert _resolve_reasoning_kwargs("high") == {"reasoning": {"effort": "high"}}


def test_resolve_reasoning_kwargs_for_int_budget() -> None:
    assert _resolve_reasoning_kwargs(2048) == {"reasoning": {"max_tokens": 2048}}


def test_resolve_reasoning_kwargs_none_is_empty() -> None:
    assert _resolve_reasoning_kwargs(None) == {}


def test_build_llm_returns_thinking_llm_when_thinking_set() -> None:
    llm = build_llm(
        model_kwargs={"model": "x", "api_key": "y", "base_url": "https://openrouter.ai/api/v1"},
        thinking="high",
        on_token=None,
        on_reasoning_token=None,
    )
    assert isinstance(llm, ThinkingLLM)


def test_build_llm_returns_plain_llm_when_no_thinking() -> None:
    from lingo import LLM
    llm = build_llm(
        model_kwargs={"model": "x", "api_key": "y", "base_url": "https://openrouter.ai/api/v1"},
        thinking=None,
        on_token=None,
        on_reasoning_token=None,
    )
    assert type(llm) is LLM  # exact type, not a subclass


def test_build_llm_ignores_thinking_for_non_openrouter() -> None:
    from lingo import LLM
    llm = build_llm(
        model_kwargs={"model": "x", "api_key": "y", "base_url": "http://localhost:1234/v1"},
        thinking="high",
        on_token=None,
        on_reasoning_token=None,
    )
    assert type(llm) is LLM


@pytest.mark.asyncio
async def test_thinking_llm_routes_reasoning_chunks() -> None:
    """Mock the OpenAI client's stream and verify on_reasoning_token sees reasoning deltas."""
    from lingo import Message

    reasoning_seen: list[str] = []
    content_seen: list[str] = []

    def on_token(t: str) -> None:
        content_seen.append(t)

    def on_reasoning_token(t: str) -> None:
        reasoning_seen.append(t)

    llm = ThinkingLLM(
        model="x",
        api_key="y",
        base_url="https://openrouter.ai/api/v1",
        on_token=on_token,
        on_reasoning_token=on_reasoning_token,
        reasoning={"effort": "high"},
    )

    from types import SimpleNamespace

    def make_chunk(content=None, reasoning=None, usage=None):
        # Plain namespace so getattr returns None for unset fields
        # (MagicMock would auto-create attributes and confuse the
        # multi-field reasoning reader).
        delta = SimpleNamespace(content=content, reasoning=reasoning)
        choice = SimpleNamespace(delta=delta)
        return SimpleNamespace(choices=[choice], usage=usage)

    chunks = [
        make_chunk(reasoning="thinking..."),
        make_chunk(reasoning=" more"),
        make_chunk(content="hello"),
        make_chunk(content=" world"),
    ]

    async def fake_stream():
        for c in chunks:
            yield c

    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_stream())
    llm.client = fake_client

    result = await llm.chat([Message.user("hi")])

    assert "".join(reasoning_seen) == "thinking... more"
    assert "".join(content_seen) == "hello world"
    assert result.content == "hello world"
    create_kwargs = fake_client.chat.completions.create.await_args.kwargs
    assert create_kwargs["reasoning"] == {"effort": "high"}
