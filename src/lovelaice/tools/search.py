"""Search tools: glob and grep, both rooted at cwd (the workspace root)."""
from __future__ import annotations

import re
from pathlib import Path

import pathspec


def _gitignore_spec() -> pathspec.PathSpec | None:
    """Load .gitignore from cwd, if present, into a PathSpec."""
    gi = Path(".gitignore")
    if not gi.is_file():
        return None
    return pathspec.PathSpec.from_lines("gitignore", gi.read_text().splitlines())


async def glob(pattern: str) -> list[str]:
    """
    Return paths matching `pattern` (e.g., "src/**/*.py"), as forward-slash
    strings relative to cwd. Patterns follow Python's pathlib glob syntax.

    Honors `.gitignore` if present at the workspace root: ignored entries
    are filtered from the result. Always excludes `.git/`.
    """
    spec = _gitignore_spec()
    results: list[str] = []
    for p in Path(".").glob(pattern):
        rel = p.as_posix()
        if rel.startswith(".git/") or rel == ".git":
            continue
        if spec is not None and spec.match_file(rel):
            continue
        results.append(rel)
    return sorted(results)


async def grep(pattern: str, path: str = ".") -> str:
    """
    Search files under `path` for `pattern` (treated as a regex). Returns
    matching lines formatted as `path:line:text`, capped at 200 hits. Use
    `bash("rg ...")` for richer search if ripgrep is on the PATH.

    Honors `.gitignore`. Skips binary files (any file containing a NUL byte
    in its first 1024 bytes).
    """
    spec = _gitignore_spec()
    regex = re.compile(pattern)
    hits: list[str] = []

    base = Path(path)
    iterator = base.rglob("*") if base.is_dir() else [base]
    for p in iterator:
        if not p.is_file():
            continue
        rel = p.as_posix()
        if rel.startswith(".git/"):
            continue
        if spec is not None and spec.match_file(rel):
            continue
        try:
            head = p.read_bytes()[:1024]
            if b"\x00" in head:
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                hits.append(f"{rel}:{i}:{line}")
                if len(hits) >= 200:
                    return "\n".join(hits) + "\n... (truncated at 200 hits)"
    return "\n".join(hits)
