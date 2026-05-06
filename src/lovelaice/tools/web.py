"""HTTP fetch tool. Returns text bodies as-is, HTML as markdown."""
from __future__ import annotations

import httpx
from markdownify import markdownify
from readabilipy import simple_json_from_html_string


MAX_BYTES = 50 * 1024


async def fetch(url: str) -> str:
    """
    GET `url`, follow redirects, and return the body as text.

    For `text/html` responses, the page is run through readabilipy to
    extract the readable article and then converted to Markdown via
    markdownify. Other text/* content types are returned verbatim.

    Output is capped at ~50 KB; longer bodies are truncated with a
    `... (truncated)` marker appended.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, follow_redirects=True)
    resp.raise_for_status()

    ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
    if ctype == "text/html":
        try:
            article = simple_json_from_html_string(resp.text, use_readability=True)
            content_html = article.get("content") or resp.text
        except Exception:
            content_html = resp.text
        body = markdownify(content_html, heading_style="ATX")
    else:
        body = resp.text

    if len(body) > MAX_BYTES:
        body = body[:MAX_BYTES] + "\n... (truncated)"
    return body
