"""Tests for the fetch tool. Mocks httpx so no network."""
from __future__ import annotations

import pytest


class FakeResponse:
    def __init__(self, body: str, content_type: str) -> None:
        self.text = body
        self.headers = {"content-type": content_type}
        self.content = body.encode("utf-8") if isinstance(body, str) else body
        self.status_code = 200

    def raise_for_status(self) -> None:
        return None


class FakeClient:
    def __init__(self, body: str, content_type: str) -> None:
        self._body = body
        self._content_type = content_type

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, follow_redirects=True):
        return FakeResponse(self._body, self._content_type)


def _patch_httpx(monkeypatch, body: str, content_type: str) -> None:
    from lovelaice.tools import web as web_module
    monkeypatch.setattr(
        web_module.httpx, "AsyncClient",
        lambda *a, **kw: FakeClient(body, content_type),
    )


@pytest.mark.asyncio
async def test_fetch_returns_text_for_text_content(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_httpx(monkeypatch, "plain text body", "text/plain; charset=utf-8")
    from lovelaice.tools import fetch
    out = await fetch("https://example.com/foo.txt")
    assert "plain text body" in out


@pytest.mark.asyncio
async def test_fetch_converts_html_to_markdown(monkeypatch: pytest.MonkeyPatch) -> None:
    html = "<html><body><h1>Hi</h1><p>World</p></body></html>"
    _patch_httpx(monkeypatch, html, "text/html; charset=utf-8")
    from lovelaice.tools import fetch
    out = await fetch("https://example.com/foo.html")
    assert "Hi" in out
    assert "<html>" not in out


@pytest.mark.asyncio
async def test_fetch_caps_at_50kb(monkeypatch: pytest.MonkeyPatch) -> None:
    big = "x" * (60 * 1024)
    _patch_httpx(monkeypatch, big, "text/plain")
    from lovelaice.tools import fetch
    out = await fetch("https://example.com/big.txt")
    assert len(out) <= 50 * 1024 + 200
    assert "truncated" in out.lower()
