"""A minimal fake OpenRouter server for end-to-end CLI testing.

Stands up an `http.server.ThreadingHTTPServer` on an ephemeral port and
serves OpenAI-compatible streaming chat completions. The streamed
chunks include `delta.reasoning` fragments so we can verify lovelaice's
reasoning passthrough renders the way real OpenRouter responses would.

Only the streaming `chat/completions` path is implemented — non-stream
(``parse()``) is not, so this is intended for tests that drive a single
streaming `chat()` call (no ReAct loop / structured output).
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Iterable


def make_chunk(
    *,
    reasoning: str | None = None,
    content: str | None = None,
    usage: dict[str, int] | None = None,
    finish_reason: str | None = None,
) -> dict[str, Any]:
    """Build one OpenAI-compatible streaming chunk dict."""
    delta: dict[str, Any] = {}
    if reasoning is not None:
        delta["reasoning"] = reasoning
    if content is not None:
        delta["content"] = content

    chunk: dict[str, Any] = {
        "id": "chatcmpl-fake",
        "object": "chat.completion.chunk",
        "created": 1700000000,
        "model": "fake-thinking-model",
        "choices": [
            {
                "index": 0,
                "delta": delta,
                "finish_reason": finish_reason,
            }
        ],
    }
    if usage is not None:
        # When usage lands, OpenAI sends an empty-choices chunk.
        chunk["choices"] = []
        chunk["usage"] = usage
    return chunk


DEFAULT_REASONING_CHUNKS: list[str] = [
    "Let me think about this. ",
    "The user said hi, ",
    "so a short, friendly reply is appropriate.",
]
DEFAULT_CONTENT_CHUNKS: list[str] = [
    "Hello! ",
    "Nice to meet you.",
]


def default_chunks() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in DEFAULT_REASONING_CHUNKS:
        out.append(make_chunk(reasoning=r))
    for c in DEFAULT_CONTENT_CHUNKS:
        out.append(make_chunk(content=c))
    out.append(make_chunk(finish_reason="stop"))
    out.append(
        make_chunk(
            usage={"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18}
        )
    )
    return out


class _Handler(BaseHTTPRequestHandler):
    # Class attribute set by start_fake_openrouter().
    chunks: list[dict[str, Any]] = []

    def do_POST(self) -> None:
        if not self.path.endswith("/chat/completions"):
            self.send_error(404, "not found")
            return

        # Drain the request body (we don't need it, but the client expects us to).
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length:
            self.rfile.read(length)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        for chunk in self.chunks:
            payload = b"data: " + json.dumps(chunk).encode("utf-8") + b"\n\n"
            self.wfile.write(payload)
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    # Silence the default access log so test output stays clean.
    def log_message(self, *_args: Any, **_kw: Any) -> None:
        return


class FakeServer:
    """Wraps a `ThreadingHTTPServer` running in a daemon thread."""

    def __init__(self, chunks: Iterable[dict[str, Any]] | None = None):
        # Build a fresh handler subclass per server so parallel tests don't share chunks.
        handler_cls = type("_Handler", (_Handler,), {"chunks": list(chunks or default_chunks())})
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def port(self) -> int:
        return self._server.server_address[1]

    @property
    def base_url(self) -> str:
        # Substring 'openrouter.ai' is needed so lovelaice's `build_llm`
        # treats this as an OpenRouter base and wires reasoning passthrough.
        return f"http://127.0.0.1:{self.port}/openrouter.ai/v1"

    def __enter__(self) -> "FakeServer":
        self._thread.start()
        return self

    def __exit__(self, *_a: Any) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2.0)
