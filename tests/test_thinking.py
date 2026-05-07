"""Translate the user-facing `thinking=` knob into a lingo `LLM` with
reasoning passthrough wired up. The streaming behavior itself is tested
in lingo (`tests/test_llm_reasoning.py`); here we only cover the
translation layer.
"""
from __future__ import annotations

import pytest

from lingo import LLM
from lovelaice.thinking import _resolve_reasoning_kwargs, build_llm


def test_resolve_reasoning_kwargs_for_effort_levels() -> None:
    assert _resolve_reasoning_kwargs("low") == {"effort": "low"}
    assert _resolve_reasoning_kwargs("medium") == {"effort": "medium"}
    assert _resolve_reasoning_kwargs("high") == {"effort": "high"}


def test_resolve_reasoning_kwargs_for_int_budget() -> None:
    assert _resolve_reasoning_kwargs(2048) == {"max_tokens": 2048}


def test_resolve_reasoning_kwargs_none_is_none() -> None:
    assert _resolve_reasoning_kwargs(None) is None


def test_resolve_reasoning_kwargs_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        _resolve_reasoning_kwargs("ridiculous")


def test_build_llm_wires_reasoning_for_openrouter() -> None:
    captured: dict[str, str] = {}

    def cb(t: str) -> None:
        captured["last"] = t

    llm = build_llm(
        model_kwargs={"model": "x", "api_key": "y", "base_url": "https://openrouter.ai/api/v1"},
        thinking="high",
        on_token=None,
        on_reasoning_token=cb,
    )
    assert isinstance(llm, LLM)
    assert llm._reasoning == {"effort": "high"}
    assert llm._on_reasoning_token is cb


def test_build_llm_no_reasoning_when_thinking_unset() -> None:
    llm = build_llm(
        model_kwargs={"model": "x", "api_key": "y", "base_url": "https://openrouter.ai/api/v1"},
        thinking=None,
        on_token=None,
        on_reasoning_token=lambda _t: None,
    )
    assert isinstance(llm, LLM)
    assert llm._reasoning is None
    # Without thinking, the reasoning callback is suppressed too —
    # there's nothing for it to fire on.
    assert llm._on_reasoning_token is None


def test_build_llm_ignores_thinking_for_non_openrouter() -> None:
    llm = build_llm(
        model_kwargs={"model": "x", "api_key": "y", "base_url": "http://localhost:1234/v1"},
        thinking="high",
        on_token=None,
        on_reasoning_token=lambda _t: None,
    )
    assert isinstance(llm, LLM)
    assert llm._reasoning is None
    assert llm._on_reasoning_token is None
