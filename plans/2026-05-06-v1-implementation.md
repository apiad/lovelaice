# Lovelaice v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish-and-extend the lovelaice v0.7 scaffold into a v1 release: a sovereign coding agent with a full-screen Textual TUI, a Rich-driven one-shot mode, OpenRouter reasoning-passthrough thinking mode, chdir-to-workspace-root grounding, and an MCP-compatible tool surface (`bash read write edit list glob grep fetch` + `mcp:server:tool` naming).

**Architecture:** Python 3.13 package. Core agent loop wraps `lingo.Lingo` with a thinking-aware `LLM` subclass and a fixed ReAct command. Two CLI modes: interactive Textual app vs. one-shot Rich renderer (auto-detected from a prompt arg + tty status). MCP servers run as stdio subprocesses spawned during `Config.build()`. Reference design: `repos/lovelaice/plans/2026-05-06-v1-design.md`.

**Tech Stack:** Python 3.13, `lingo-ai==1.0`, `typer`, `rich`, `textual`, `mcp` (Python SDK), `httpx`, `markdownify`, `readabilipy`, `pathspec`, `pytest`, `pytest-asyncio`, `uv` for dependency management.

---

## Conventions used throughout this plan

- Repo root for all paths: `repos/lovelaice/`. Run all commands from that directory unless noted.
- Test runner: `uv run pytest`. Async tests: `pytest-asyncio` in auto mode (configured in `pyproject.toml` via Task 1).
- Commit style: conventional commits (`feat:`, `fix:`, `test:`, `refactor:`, `chore:`). One commit per task unless explicitly noted otherwise.
- "Engineer" below = whoever (or whatever) is executing the plan; treat instructions as written, do not skip TDD steps.

---

## Phase 1 — Foundations

### Task 1: Add dependencies and pytest setup

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/__init__.py` (empty)
- Create: `tests/conftest.py`

- [ ] **Step 1: Update `pyproject.toml` dependencies and add test extras.**

Replace the existing `[project]` and `[build-system]` blocks (and append the new sections) so the file looks like this:

```toml
[project]
name = "lovelaice"
version = "1.0.0"
description = "A local-first coding agent for the terminal, with Python-defined commands and tools."
readme = "README.md"
authors = [
    { name = "Alejandro Piad", email = "apiad@apiad.net" }
]
requires-python = ">=3.13"
dependencies = [
    "lingo-ai==1.0",
    "python-dotenv>=1.2.1",
    "rich>=14.2.0",
    "typer>=0.21.1",
    "textual>=0.85",
    "mcp>=1.2",
    "httpx>=0.28",
    "markdownify>=0.13",
    "readabilipy>=0.3",
    "pathspec>=0.12",
]

[dependency-groups]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "pytest-mock>=3.14",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project.scripts]
lovelaice = "lovelaice.cli:app"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Resolve the lockfile.**

Run: `uv sync --all-groups`
Expected: `uv.lock` is updated; no errors. Confirms all new deps resolve.

- [ ] **Step 3: Create `tests/__init__.py`.**

```python
```

(Empty file — just makes `tests/` a package so `conftest.py` is discovered.)

- [ ] **Step 4: Create `tests/conftest.py`.**

```python
"""Shared fixtures for the lovelaice test suite."""
from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture
def workspace_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A scratch directory with a stub .lovelaice.py, used as the cwd."""
    config = tmp_path / ".lovelaice.py"
    config.write_text("from lovelaice import Config\nconfig = Config(models={'default': {'model': 'x'}}, prompt='x')\n")
    monkeypatch.chdir(tmp_path)
    return tmp_path
```

- [ ] **Step 5: Smoke-test pytest.**

Run: `uv run pytest -q`
Expected: `no tests ran` (and no errors). Confirms pytest, asyncio mode, and conftest load cleanly.

- [ ] **Step 6: Commit.**

```bash
git add pyproject.toml uv.lock tests/__init__.py tests/conftest.py
git commit -m "chore: add v1 deps (textual, mcp, httpx, markdownify, readabilipy, pathspec) + pytest setup"
```

---

### Task 2: Workspace grounding — chdir + missing-config error

**Files:**
- Modify: `src/lovelaice/cli.py:30-66` (the `main` callback and config-finding flow)
- Test: `tests/test_workspace_grounding.py`

The existing `find_config_file` (in `config.py`) already walks up correctly. We need to:
1. `os.chdir()` to the directory containing `.lovelaice.py` immediately after finding it.
2. Pass the file *name* (not path) to `load_agent_from_config` (since cwd is now its dir).
3. Improve the missing-config error.

- [ ] **Step 1: Write the failing test.**

Create `tests/test_workspace_grounding.py`:

```python
"""Workspace grounding: chdir to .lovelaice.py's directory before agent runs."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from lovelaice.config import find_config_file


def test_find_config_file_walks_upward(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given .lovelaice.py at the root and cwd in a deep subdir, find_config_file
    returns the root config."""
    (tmp_path / ".lovelaice.py").write_text("# stub\n")
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    monkeypatch.chdir(deep)

    found = find_config_file()
    assert found is not None
    assert found.resolve() == (tmp_path / ".lovelaice.py").resolve()


def test_find_config_file_returns_none_when_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No .lovelaice.py anywhere up the tree → returns None."""
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    monkeypatch.chdir(deep)

    assert find_config_file(start_path=deep) is None
```

- [ ] **Step 2: Run the tests; verify the first passes already and the second too.**

Run: `uv run pytest tests/test_workspace_grounding.py -v`
Expected: 2 PASS. (`find_config_file` already works in v0.7.) These tests lock down the behavior we depend on; they are not the change itself.

- [ ] **Step 3: Modify `src/lovelaice/cli.py` to chdir on startup.**

Replace the `main` callback (lines 30-66) with this version (note: imports already include `Path`; we add `os`):

```python
@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    prompt_parts: Annotated[
        Optional[List[str]],
        typer.Argument(help="The task or question for the agent.", show_default=False),
    ] = None,
    init: Annotated[
        bool,
        typer.Option("--init", help="Write a starter .lovelaice.py in the current directory."),
    ] = False,
    model: Annotated[
        Optional[str],
        typer.Option("--model", "-m", help="Named model alias from .lovelaice.py."),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show full tool output (one-shot mode)."),
    ] = False,
):
    """
    Lovelaice — a sovereign coding agent for the terminal.

    With no arguments, opens a full-screen TUI. With a prompt, runs a
    single agentic turn and streams to stdout.
    """
    if init:
        _do_init()
        raise typer.Exit()

    config_path = find_config_file()
    if config_path is None:
        typer.echo(
            "No .lovelaice.py found in this directory or any ancestor. "
            "Run `lovelaice --init` to create one.",
            err=True,
        )
        raise typer.Exit(1)

    # Ground the workspace: chdir to where .lovelaice.py lives, then load it
    # by basename so any relative imports in the config see the new cwd.
    os.chdir(config_path.parent)
    config_path = Path(".lovelaice.py")

    prompt = " ".join(prompt_parts) if prompt_parts else ""

    if prompt:
        from .oneshot import run_oneshot
        asyncio.run(run_oneshot(config_path, model=model, prompt=prompt, verbose=verbose))
    else:
        from .tui.app import run_tui
        asyncio.run(run_tui(config_path, model=model))
```

Also add the import at the top of `cli.py` (next to existing `import asyncio`):

```python
import os
```

Remove the old `_run_once` and `_run_interactive` functions (lines 92-140) — they will be replaced by `oneshot.py` and `tui/app.py` in later tasks. Also remove the `_LiveChat` class (lines 143-165). Also remove now-unused imports (`getpass`, `datetime`, `Console`, `Live`, `Markdown`, `Panel`, `Prompt`, `Lingo`-related). Keep what `_do_init` still needs (`typer`, `inspect`, `Path`).

After this edit, `cli.py` will fail to import because `oneshot.py` and `tui/app.py` don't exist yet. That's fine — we'll add them in Phase 4 and Phase 5. Until then the CLI is broken, and the test suite shouldn't import `cli`.

- [ ] **Step 4: Add a test that asserts the CLI exits with code 1 when there's no config.**

Append to `tests/test_workspace_grounding.py`:

```python
import subprocess
import sys


def test_cli_exits_when_no_config(tmp_path: Path) -> None:
    """Running `lovelaice` from a directory with no ancestor .lovelaice.py
    exits 1 with a helpful message."""
    result = subprocess.run(
        [sys.executable, "-m", "lovelaice", "hello"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "No .lovelaice.py" in result.stderr
```

We have to add a `__main__.py` for `python -m lovelaice` to work. Create `src/lovelaice/__main__.py`:

```python
from lovelaice.cli import app

if __name__ == "__main__":
    app()
```

- [ ] **Step 5: Run the test.**

Run: `uv run pytest tests/test_workspace_grounding.py::test_cli_exits_when_no_config -v`
Expected: PASS (because `cli.py`'s import of `oneshot`/`tui` is *deferred* inside the `main` callback — it only triggers when a config IS found, which here it isn't).

If this fails because of import errors at the module level, the engineer must move `from .oneshot import run_oneshot` and `from .tui.app import run_tui` to *inside* the relevant branches (already done above) so importing `cli` itself doesn't blow up.

- [ ] **Step 6: Commit.**

```bash
git add src/lovelaice/cli.py src/lovelaice/__main__.py tests/test_workspace_grounding.py
git commit -m "feat: chdir to workspace root on startup; clearer no-config error"
```

---

### Task 3: Fix the broken ReAct loop

**Files:**
- Modify: `src/lovelaice/commands/react.py`
- Test: `tests/test_react.py`

The v0.7 react calls `engine.act(context)`, which does not exist on `lingo.Engine`. The correct primitive is `engine.equip(...)` → `engine.invoke(...)`, mirroring `lingo.flow.Act.execute`. Also fix the tool-result message: it should be `Message.tool(...)` of the result dump, not a system message with a string concat.

- [ ] **Step 1: Write the failing test.**

Create `tests/test_react.py`:

```python
"""ReAct loop semantics, isolated from the LLM."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from lingo import Context, Message
from lingo.tools import ToolResult

from lovelaice.commands.react import react


@pytest.mark.asyncio
async def test_react_stops_when_decide_returns_true() -> None:
    """The loop calls engine.decide, gets True, skips equip/invoke, calls reply."""
    context = Context([Message.user("hi")])
    engine = MagicMock()
    engine.decide = AsyncMock(return_value=True)
    engine.equip = AsyncMock()
    engine.invoke = AsyncMock()
    engine.reply = AsyncMock(return_value=Message.assistant("done"))

    await react(context, engine)

    engine.decide.assert_awaited_once()
    engine.equip.assert_not_awaited()
    engine.invoke.assert_not_awaited()
    engine.reply.assert_awaited_once()
    assert context.messages[-1].content == "done"


@pytest.mark.asyncio
async def test_react_uses_equip_then_invoke_when_not_done() -> None:
    """If decide returns False, the loop calls equip() then invoke() and appends a tool message."""
    context = Context([Message.user("hi")])
    engine = MagicMock()
    fake_tool = MagicMock(name="bash")
    engine.decide = AsyncMock(side_effect=[False, True])  # one act-iteration, then done
    engine.equip = AsyncMock(return_value=fake_tool)
    engine.invoke = AsyncMock(return_value=ToolResult(tool="bash", result="hello"))
    engine.reply = AsyncMock(return_value=Message.assistant("ok"))

    await react(context, engine)

    engine.equip.assert_awaited_once_with(context)
    engine.invoke.assert_awaited_once_with(context, fake_tool)
    # Tool result should be appended as a Message.tool(...) carrying the dump.
    assert any(m.role == "tool" for m in context.messages)


@pytest.mark.asyncio
async def test_react_handles_invoke_error() -> None:
    """If invoke raises (returns ToolResult with error), append error observation and continue."""
    context = Context([Message.user("hi")])
    engine = MagicMock()
    fake_tool = MagicMock(name="bash")
    engine.decide = AsyncMock(side_effect=[False, True])
    engine.equip = AsyncMock(return_value=fake_tool)
    engine.invoke = AsyncMock(return_value=ToolResult(tool="bash", error="boom"))
    engine.reply = AsyncMock(return_value=Message.assistant("recovered"))

    await react(context, engine)

    # Error should be visible in the context as a tool message
    tool_msgs = [m for m in context.messages if m.role == "tool"]
    assert len(tool_msgs) == 1
    assert "boom" in str(tool_msgs[0].content)
```

- [ ] **Step 2: Run; expect failures.**

Run: `uv run pytest tests/test_react.py -v`
Expected: FAIL on the second and third tests because v0.7's react calls the nonexistent `engine.act`.

- [ ] **Step 3: Fix `src/lovelaice/commands/react.py`.**

Replace the file contents:

```python
from lingo import Context, Engine, Message


REACT_HEADER = """
You are operating as an autonomous agent in a tool-use loop.

On each step you can either call one of the registered tools to make
progress on the user's task, or stop the loop and reply directly to
the user with the final answer.

Call tools whenever you need to read, modify, or inspect anything in
the environment. Stop only when you have everything you need to give
a complete answer. Do not narrate plans without acting on them.
""".strip()


DONE_INSTRUCTION = (
    "Has the user's most recent request been fully resolved by the work done so far? "
    "Answer True only if the next message to the user can be the final answer with "
    "no further tool calls. Answer False if there is still investigation, modification, "
    "or verification left to do."
)


async def react(context: Context, engine: Engine, *, max_steps: int = 20) -> None:
    """
    Generalist ReAct loop: decide-equip-invoke until the LLM signals done.

    Each iteration:
      1. Ask the LLM whether the user's request is fully resolved.
      2. If yes, exit the loop.
      3. Otherwise, equip a tool (LLM picks from the registered set),
         invoke it (LLM fills in parameters), and append the ToolResult
         as a `tool`-role message in the context.

    After the loop, ask the LLM for a final natural-language reply.
    """
    context.append(Message.system(REACT_HEADER))

    for _ in range(max_steps):
        done = await engine.decide(context, DONE_INSTRUCTION)
        if done:
            break

        tool = await engine.equip(context)
        result = await engine.invoke(context, tool)
        context.append(Message.tool(result.model_dump()))

    final = await engine.reply(
        context,
        "Reply to the user now with a concise summary of what was done and the answer to their request.",
    )
    context.append(final)
```

- [ ] **Step 4: Run; expect pass.**

Run: `uv run pytest tests/test_react.py -v`
Expected: all 3 PASS.

- [ ] **Step 5: Commit.**

```bash
git add src/lovelaice/commands/react.py tests/test_react.py
git commit -m "fix(react): use engine.equip + engine.invoke (engine.act doesn't exist)"
```

---

## Phase 2 — Tool surface

### Task 4: `bash` tool with timeout

**Files:**
- Modify: `src/lovelaice/tools/bash.py`
- Test: `tests/test_tool_bash.py`

The v0.7 `bash` shells out without a timeout. Add a 120-second default and a `BASH_TIMEOUT` module-level knob that `Config(bash_timeout=...)` will mutate (Task 8 wires `Config` to set it).

- [ ] **Step 1: Write the failing test.**

Create `tests/test_tool_bash.py`:

```python
"""Tests for the bash tool."""
from __future__ import annotations

import pytest

from lovelaice.tools import bash as bash_module


@pytest.mark.asyncio
async def test_bash_returns_combined_stdout_stderr() -> None:
    out = await bash_module.bash("echo hi; echo err 1>&2")
    assert "hi" in out
    assert "err" in out


@pytest.mark.asyncio
async def test_bash_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    """A long-running command honors the timeout knob."""
    monkeypatch.setattr(bash_module, "BASH_TIMEOUT", 0.5)
    with pytest.raises(TimeoutError) as ei:
        await bash_module.bash("sleep 5")
    assert "timed out" in str(ei.value).lower()


@pytest.mark.asyncio
async def test_bash_nonzero_exit_returns_output() -> None:
    """A nonzero exit doesn't raise; the output (incl. stderr) is returned."""
    out = await bash_module.bash("false; echo done")
    assert "done" in out
```

- [ ] **Step 2: Run; expect failures.**

Run: `uv run pytest tests/test_tool_bash.py -v`
Expected: FAILs (current `bash` has no timeout, may also not raise `TimeoutError`).

- [ ] **Step 3: Replace `src/lovelaice/tools/bash.py`.**

```python
"""Bash tool: yolo subprocess execution with a configurable timeout.

`Config(bash_timeout=...)` mutates `BASH_TIMEOUT` at build-time; the
default is 120 seconds.
"""
from __future__ import annotations

import asyncio


BASH_TIMEOUT: float = 120.0


async def bash(command: str) -> str:
    """
    Run `command` in a shell. Returns combined stdout+stderr in invocation
    order. Nonzero exit codes do not raise — the output is returned and the
    agent decides what to do.

    Times out after BASH_TIMEOUT seconds; on timeout, the subprocess is
    SIGTERM'd (then SIGKILL'd 1 second later if still alive) and a
    TimeoutError is raised.
    """
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,  # combine stderr into stdout
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=BASH_TIMEOUT)
    except asyncio.TimeoutError:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
        raise TimeoutError(f"bash timed out after {BASH_TIMEOUT}s")

    return stdout.decode("utf-8", errors="replace")
```

- [ ] **Step 4: Run; expect pass.**

Run: `uv run pytest tests/test_tool_bash.py -v`
Expected: all 3 PASS.

- [ ] **Step 5: Commit.**

```bash
git add src/lovelaice/tools/bash.py tests/test_tool_bash.py
git commit -m "feat(tools): bash gains timeout (default 120s) and combined stdout+stderr"
```

---

### Task 5: Rename `list_dir` → `list_` (display name `list`)

**Files:**
- Modify: `src/lovelaice/tools/files.py`
- Modify: `src/lovelaice/tools/__init__.py`
- Test: `tests/test_tool_files.py`

The display name `list` is reserved by Python's builtin, so we keep the function as `list_` internally and let `Config.tool(list_, name="list")` (Task 8) override the display.

- [ ] **Step 1: Write the failing test.**

Create `tests/test_tool_files.py`:

```python
"""Tests for the file tools."""
from __future__ import annotations

from pathlib import Path

import pytest

from lovelaice.tools import edit, list_, read, write


@pytest.mark.asyncio
async def test_list_underscore_returns_sorted_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "b").write_text("")
    (tmp_path / "a").write_text("")
    assert await list_() == ["a", "b"]


@pytest.mark.asyncio
async def test_list_underscore_explicit_path(tmp_path: Path) -> None:
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "x").write_text("")
    assert await list_(str(sub)) == ["x"]


@pytest.mark.asyncio
async def test_read_write_edit_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "f.txt"
    await write(str(p), "hello world")
    assert await read(str(p)) == "hello world"
    await edit(str(p), "world", "lovelaice")
    assert await read(str(p)) == "hello lovelaice"
```

- [ ] **Step 2: Run; expect ImportError on `list_`.**

Run: `uv run pytest tests/test_tool_files.py -v`
Expected: FAIL with `ImportError: cannot import name 'list_'`.

- [ ] **Step 3: Modify `src/lovelaice/tools/files.py`.**

Replace the `list_dir` function definition with `list_` (signature unchanged):

```python
async def list_(path: str = ".") -> list[str]:
    """
    List the entries in a directory. Returns a flat, sorted list of names
    (not recursive). Use `bash("find ...")` for recursive listings.
    """
    return sorted(os.listdir(path))
```

- [ ] **Step 4: Update `src/lovelaice/tools/__init__.py`.**

Replace its contents:

```python
"""Built-in tools for lovelaice agents."""
from .bash import bash
from .files import edit, list_, read, write
# `glob`, `grep`, `fetch` arrive in Tasks 6–8.
```

- [ ] **Step 5: Run; expect pass.**

Run: `uv run pytest tests/test_tool_files.py -v`
Expected: all 3 PASS.

- [ ] **Step 6: Commit.**

```bash
git add src/lovelaice/tools/files.py src/lovelaice/tools/__init__.py tests/test_tool_files.py
git commit -m "refactor(tools): rename list_dir to list_ (display name 'list' via Config.tool)"
```

---

### Task 6: `glob` tool

**Files:**
- Create: `src/lovelaice/tools/search.py`
- Modify: `src/lovelaice/tools/__init__.py`
- Test: `tests/test_tool_search.py`

`glob` walks the workspace from cwd and applies a `**/*`-style pattern. Honors `.gitignore` via `pathspec` if a `.gitignore` exists at cwd.

- [ ] **Step 1: Write the failing test.**

Create `tests/test_tool_search.py`:

```python
"""Tests for glob and grep."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_glob_matches_recursive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lovelaice.tools import glob as glob_tool

    monkeypatch.chdir(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("")
    (tmp_path / "src" / "b.txt").write_text("")
    (tmp_path / "README.md").write_text("")

    py_files = await glob_tool("**/*.py")
    assert "src/a.py" in py_files
    assert "src/b.txt" not in py_files


@pytest.mark.asyncio
async def test_glob_respects_gitignore(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lovelaice.tools import glob as glob_tool

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".gitignore").write_text("ignored/\n*.log\n")
    (tmp_path / "ignored").mkdir()
    (tmp_path / "ignored" / "x.py").write_text("")
    (tmp_path / "kept.py").write_text("")
    (tmp_path / "noisy.log").write_text("")

    files = await glob_tool("**/*")
    assert "kept.py" in files
    assert "ignored/x.py" not in files
    assert "noisy.log" not in files
```

- [ ] **Step 2: Run; expect ImportError.**

Run: `uv run pytest tests/test_tool_search.py -v`
Expected: FAIL with `ImportError: cannot import name 'glob'`.

- [ ] **Step 3: Create `src/lovelaice/tools/search.py`.**

```python
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
    return pathspec.PathSpec.from_lines("gitwildmatch", gi.read_text().splitlines())


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
    iterator = (base.rglob("*") if base.is_dir() else [base])
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
```

- [ ] **Step 4: Update `tools/__init__.py`.**

```python
"""Built-in tools for lovelaice agents."""
from .bash import bash
from .files import edit, list_, read, write
from .search import glob, grep
# `fetch` arrives in Task 7.
```

- [ ] **Step 5: Run; expect pass.**

Run: `uv run pytest tests/test_tool_search.py -v -k glob`
Expected: 2 PASS (the glob tests; grep tests come in Task 7's grep section).

- [ ] **Step 6: Commit.**

```bash
git add src/lovelaice/tools/search.py src/lovelaice/tools/__init__.py tests/test_tool_search.py
git commit -m "feat(tools): add glob (gitignore-aware) and grep stub in tools/search.py"
```

---

### Task 7: `grep` tool tests + `fetch` tool

**Files:**
- Modify: `tests/test_tool_search.py` (add grep tests)
- Create: `src/lovelaice/tools/web.py`
- Modify: `src/lovelaice/tools/__init__.py`
- Test: `tests/test_tool_web.py`

`grep` is already implemented in Task 6 (in `search.py`). This task adds tests for it and ships `fetch`.

- [ ] **Step 1: Add grep tests to `tests/test_tool_search.py`.**

Append to the existing file:

```python
@pytest.mark.asyncio
async def test_grep_returns_path_line_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lovelaice.tools import grep

    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.txt").write_text("foo\nbar\nbaz\n")
    (tmp_path / "b.txt").write_text("nothing\nfoo\n")

    out = await grep("foo")
    assert "a.txt:1:foo" in out
    assert "b.txt:2:foo" in out


@pytest.mark.asyncio
async def test_grep_caps_at_200(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lovelaice.tools import grep

    monkeypatch.chdir(tmp_path)
    (tmp_path / "many.txt").write_text("\n".join(["match"] * 500))

    out = await grep("match")
    # 200 hits + the truncation marker
    assert out.count(":") >= 200  # path:line:text per hit
    assert "truncated at 200 hits" in out


@pytest.mark.asyncio
async def test_grep_skips_binary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lovelaice.tools import grep

    monkeypatch.chdir(tmp_path)
    (tmp_path / "bin").write_bytes(b"\x00\x01match\x02")
    (tmp_path / "txt").write_text("match\n")

    out = await grep("match")
    assert "bin:" not in out
    assert "txt:1:match" in out
```

- [ ] **Step 2: Run; expect pass for grep.**

Run: `uv run pytest tests/test_tool_search.py -v -k grep`
Expected: 3 PASS.

- [ ] **Step 3: Write the failing fetch tests.**

Create `tests/test_tool_web.py`:

```python
"""Tests for the fetch tool. Mocks httpx so no network."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_fetch_returns_text_for_text_content(monkeypatch: pytest.MonkeyPatch) -> None:
    from lovelaice.tools import fetch
    from lovelaice.tools import web as web_module

    class FakeResponse:
        status_code = 200
        text = "plain text body"
        headers = {"content-type": "text/plain; charset=utf-8"}
        content = b"plain text body"

        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self, *a, **kw):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        async def get(self, url, follow_redirects=True):
            return FakeResponse()

    monkeypatch.setattr(web_module.httpx, "AsyncClient", FakeClient)

    out = await fetch("https://example.com/foo.txt")
    assert "plain text body" in out


@pytest.mark.asyncio
async def test_fetch_converts_html_to_markdown(monkeypatch: pytest.MonkeyPatch) -> None:
    from lovelaice.tools import fetch
    from lovelaice.tools import web as web_module

    html = "<html><body><h1>Hi</h1><p>World</p></body></html>"

    class FakeResponse:
        status_code = 200
        text = html
        headers = {"content-type": "text/html; charset=utf-8"}
        content = html.encode("utf-8")

        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self, *a, **kw):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        async def get(self, url, follow_redirects=True):
            return FakeResponse()

    monkeypatch.setattr(web_module.httpx, "AsyncClient", FakeClient)

    out = await fetch("https://example.com/foo.html")
    assert "Hi" in out
    assert "<html>" not in out  # converted to markdown


@pytest.mark.asyncio
async def test_fetch_caps_at_50kb(monkeypatch: pytest.MonkeyPatch) -> None:
    from lovelaice.tools import fetch
    from lovelaice.tools import web as web_module

    big = "x" * (60 * 1024)

    class FakeResponse:
        status_code = 200
        text = big
        headers = {"content-type": "text/plain"}
        content = big.encode()

        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, follow_redirects=True): return FakeResponse()

    monkeypatch.setattr(web_module.httpx, "AsyncClient", FakeClient)

    out = await fetch("https://example.com/big.txt")
    assert len(out) <= 50 * 1024 + 200  # allow truncation marker overhead
    assert "truncated" in out.lower()
```

- [ ] **Step 4: Create `src/lovelaice/tools/web.py`.**

```python
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
```

- [ ] **Step 5: Update `tools/__init__.py`.**

```python
"""Built-in tools for lovelaice agents."""
from .bash import bash
from .files import edit, list_, read, write
from .search import glob, grep
from .web import fetch

__all__ = ["bash", "read", "write", "edit", "list_", "glob", "grep", "fetch"]
```

- [ ] **Step 6: Run; expect pass.**

Run: `uv run pytest tests/test_tool_web.py tests/test_tool_search.py -v`
Expected: all PASS.

- [ ] **Step 7: Commit.**

```bash
git add src/lovelaice/tools/web.py src/lovelaice/tools/__init__.py tests/test_tool_search.py tests/test_tool_web.py
git commit -m "feat(tools): add fetch (httpx + readability + markdownify) and grep tests"
```

---

## Phase 3 — Thinking, MCP, Config

### Task 8: Extend `Config` with `name=`, `bash_timeout=`, `mcp=`

**Files:**
- Modify: `src/lovelaice/config.py`
- Test: `tests/test_config.py`

The v0.7 `Config.tool` accepts only the function. We need:
- `tool(func, *, name: str | None = None)` so `list_` can register as `list`.
- `Config(bash_timeout=...)` that mutates `tools.bash.BASH_TIMEOUT` at build time.
- `Config(mcp=[...])` that stores specs (MCP wiring lands in Task 10).

- [ ] **Step 1: Write the failing test.**

Create `tests/test_config.py`:

```python
"""Config extensions: name override, bash_timeout, mcp specs."""
from __future__ import annotations

import pytest

from lovelaice.config import Config


def test_config_tool_accepts_name_override() -> None:
    cfg = Config(models={"default": {"model": "x"}}, prompt="x")

    async def list_(path: str = ".") -> list[str]:
        """List."""
        return []

    cfg.tool(list_, name="list")
    assert cfg.tools[0]._name_override == "list"
    assert cfg.tools[0]._target is list_


def test_config_bash_timeout_mutates_module() -> None:
    from lovelaice.tools import bash as bash_mod

    original = bash_mod.BASH_TIMEOUT
    try:
        cfg = Config(models={"default": {"model": "x"}}, prompt="x", bash_timeout=7.5)
        cfg._apply_bash_timeout()  # called by build() in real life
        assert bash_mod.BASH_TIMEOUT == 7.5
    finally:
        bash_mod.BASH_TIMEOUT = original


def test_config_mcp_stores_specs() -> None:
    cfg = Config(
        models={"default": {"model": "x"}},
        prompt="x",
        mcp=[{"name": "fs", "command": "echo", "args": []}],
    )
    assert cfg.mcp == [{"name": "fs", "command": "echo", "args": []}]


def test_config_default_mcp_is_empty() -> None:
    cfg = Config(models={"default": {"model": "x"}}, prompt="x")
    assert cfg.mcp == []
```

- [ ] **Step 2: Run; expect failures.**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAILs (the new kwargs / methods don't exist).

- [ ] **Step 3: Replace `src/lovelaice/config.py`.**

```python
from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional

from lingo import LLM, Context, Engine

from .core import Lovelaice


def find_config_file(start_path: Path = Path(".")) -> Optional[Path]:
    """
    Walk upwards from `start_path` looking for a `.lovelaice.py` config
    file. Returns the first match, or None if none is found before the
    filesystem root.
    """
    current = start_path.resolve()
    while True:
        config_path = current / ".lovelaice.py"
        if config_path.exists():
            return config_path
        if current == current.parent:
            return None
        current = current.parent


def load_agent_from_config(config_path: Path) -> "Config":
    """
    Dynamically import the `.lovelaice.py` file at `config_path` and
    return its `config` object.
    """
    module_name = "lovelaice.local_config"

    spec = importlib.util.spec_from_file_location(module_name, config_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for {config_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception as e:
        raise RuntimeError(f"Error executing config at {config_path}: {e}")

    if not hasattr(module, "config"):
        raise AttributeError(
            f"The config at {config_path} must define a `config` variable."
        )

    return module.config


@dataclass
class _ToolEntry:
    """Internal: tool function + optional display-name override."""
    _target: Callable
    _name_override: str | None = None


class Config:
    """
    Plugin registry for a Lovelaice agent.

    `.lovelaice.py` files instantiate one of these and decorate their
    custom tools and commands onto it. The CLI then calls `build()` to
    produce a configured `Lovelaice` instance.
    """

    def __init__(
        self,
        models: dict[str, dict],
        prompt: str,
        *,
        bash_timeout: float | None = None,
        mcp: list[dict[str, Any]] | None = None,
    ):
        self.models = models
        self.default_model = next(iter(models))
        self.prompt = prompt
        self.bash_timeout = bash_timeout
        self.mcp: list[dict[str, Any]] = list(mcp or [])
        self.commands: list[Callable] = []
        self.tools: list[_ToolEntry] = []
        self.agent: Lovelaice | None = None

    def command(self, func: Callable[[Context, Engine], Coroutine]):
        """Register a Python function as a top-level agent command (workflow)."""
        self.commands.append(func)
        return func

    def tool(self, func: Callable, *, name: str | None = None):
        """
        Register a Python function as a tool. Optionally override the
        display name (e.g., to register `list_` as `"list"`).
        """
        self.tools.append(_ToolEntry(_target=func, _name_override=name))
        return func

    def _apply_bash_timeout(self) -> None:
        """Mutate the BASH_TIMEOUT module global if configured."""
        if self.bash_timeout is None:
            return
        from .tools import bash as bash_mod
        bash_mod.BASH_TIMEOUT = self.bash_timeout

    def build(self, model: str | None, on_token, on_reasoning_token=None) -> Lovelaice:
        if self.agent is not None:
            raise RuntimeError("Config.build() already called once.")

        self._apply_bash_timeout()

        model = model or self.default_model
        model_kwargs = dict(self.models[model])
        thinking = model_kwargs.pop("thinking", None)

        from .thinking import build_llm
        llm = build_llm(
            model_kwargs=model_kwargs,
            thinking=thinking,
            on_token=on_token,
            on_reasoning_token=on_reasoning_token,
        )

        self.agent = Lovelaice(llm=llm, prompt=self.prompt)

        # Register decorated tools, applying name overrides.
        for entry in self.tools:
            t = self.agent.tool(entry._target)
            if entry._name_override is not None:
                t._name = entry._name_override

        # Register MCP-loaded tools.
        if self.mcp:
            from .mcp import register_mcp_tools
            register_mcp_tools(self.agent, self.mcp)

        for cmd in self.commands:
            self.agent.skill(cmd)

        return self.agent
```

- [ ] **Step 4: Run config tests.**

Run: `uv run pytest tests/test_config.py -v`
Expected: 4 PASS. (Note: `build()` references `thinking.py` and `mcp.py` which don't exist yet — the tests don't call `build()`, so they pass.)

- [ ] **Step 5: Commit.**

```bash
git add src/lovelaice/config.py tests/test_config.py
git commit -m "feat(config): add name= override on tool(), bash_timeout=, mcp= specs"
```

---

### Task 9: `thinking.py` — OpenRouter reasoning passthrough

**Files:**
- Create: `src/lovelaice/thinking.py`
- Test: `tests/test_thinking.py`

`lingo.LLM.chat()` only routes `delta.content` to `on_token`. To capture `delta.reasoning`, we subclass `LLM` and reimplement `chat()`. We also inject the `reasoning` body kwarg.

- [ ] **Step 1: Write the failing test.**

Create `tests/test_thinking.py`:

```python
"""Thinking mode: OpenRouter `reasoning` request injection + delta.reasoning streaming."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lovelaice.thinking import ThinkingLLM, _resolve_reasoning_kwargs, build_llm


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

    # Build fake streaming chunks. Each chunk has `choices[0].delta.{content,reasoning}` and optional `usage`.
    def make_chunk(content=None, reasoning=None, usage=None):
        delta = MagicMock()
        delta.content = content
        delta.reasoning = reasoning
        choice = MagicMock(); choice.delta = delta
        chunk = MagicMock(); chunk.choices = [choice]; chunk.usage = usage
        return chunk

    chunks = [
        make_chunk(reasoning="thinking..."),
        make_chunk(reasoning=" more"),
        make_chunk(content="hello"),
        make_chunk(content=" world"),
    ]

    async def fake_stream():
        for c in chunks:
            yield c

    # Patch the underlying client.
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_stream())
    llm.client = fake_client

    result = await llm.chat([Message.user("hi")])

    assert "".join(reasoning_seen) == "thinking... more"
    assert "".join(content_seen) == "hello world"
    assert result.content == "hello world"
    # Verify reasoning kwarg was passed to the API
    create_kwargs = fake_client.chat.completions.create.await_args.kwargs
    assert create_kwargs["reasoning"] == {"effort": "high"}
```

- [ ] **Step 2: Run; expect failures.**

Run: `uv run pytest tests/test_thinking.py -v`
Expected: FAIL — `lovelaice.thinking` does not exist.

- [ ] **Step 3: Create `src/lovelaice/thinking.py`.**

```python
"""OpenRouter reasoning passthrough — extends lingo's LLM to capture
`delta.reasoning` chunks and forward them to a separate callback.

We subclass because `lingo.LLM.chat()` reads only `delta.content` and
silently drops everything else; without subclassing, reasoning tokens
would never reach the UI.
"""
from __future__ import annotations

import inspect
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
    base_url = model_kwargs.get("base_url", "")
    if thinking is None or "openrouter.ai" not in base_url:
        return LLM(on_token=on_token, **model_kwargs)
    extra = _resolve_reasoning_kwargs(thinking)
    return ThinkingLLM(
        on_token=on_token,
        on_reasoning_token=on_reasoning_token,
        **{**model_kwargs, **extra},
    )


class ThinkingLLM(LLM):
    """A `lingo.LLM` that also forwards `delta.reasoning` chunks."""

    def __init__(
        self,
        *args,
        on_reasoning_token: Callable[[str], Any] | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._on_reasoning_token = on_reasoning_token

    async def on_reasoning_token(self, token: str) -> None:
        if self._on_reasoning_token is None:
            return
        resp = self._on_reasoning_token(token)
        if inspect.iscoroutine(resp):
            await resp

    async def chat(self, messages: list[Message], **kwargs) -> Message:
        """Same as lingo.LLM.chat(), but also routes `delta.reasoning` to a separate sink."""
        content_chunks: list[str] = []
        usage: Usage | None = None
        api_messages = [msg.model_dump() for msg in messages]

        async for chunk in await self.client.chat.completions.create(
            model=self.model,  # type: ignore[arg-type]
            messages=api_messages,  # type: ignore[arg-type]
            stream=True,
            stream_options=dict(include_usage=True),  # type: ignore[arg-type]
            **(self.extra_kwargs | kwargs),
        ):
            if getattr(chunk, "usage", None):
                usage = Usage(
                    prompt_tokens=chunk.usage.prompt_tokens,
                    completion_tokens=chunk.usage.completion_tokens,
                    total_tokens=chunk.usage.total_tokens,
                )

            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            reasoning = getattr(delta, "reasoning", None)
            if reasoning:
                await self.on_reasoning_token(reasoning)

            content = getattr(delta, "content", None)
            if content:
                await self.on_token(content)
                content_chunks.append(content)

        result = Message.assistant("".join(content_chunks), usage=usage)
        await self.on_message(result)
        return result
```

- [ ] **Step 4: Run; expect pass.**

Run: `uv run pytest tests/test_thinking.py -v`
Expected: 6 PASS.

- [ ] **Step 5: Commit.**

```bash
git add src/lovelaice/thinking.py tests/test_thinking.py
git commit -m "feat: ThinkingLLM forwards OpenRouter delta.reasoning to a separate sink"
```

---

### Task 10: MCP server lifecycle + tool registration

**Files:**
- Create: `src/lovelaice/mcp.py`
- Test: `tests/test_mcp.py`

The Python `mcp` SDK provides `mcp.client.stdio.stdio_client` and `ClientSession`. We spawn one server per spec, fetch its tool list, and wrap each MCP tool as a `lingo.tools.DelegateTool` with display name `mcp:<server>:<tool>`.

Lifecycle: servers spawn at `Config.build()` time and live as long as the agent. For v1 we leak them — there's no clean shutdown surface from inside `Lovelaice` and the OS reaps them on exit. (Future work: add an `agent.close()` for the TUI to call.)

- [ ] **Step 1: Write the failing test.**

Create `tests/test_mcp.py`:

```python
"""MCP integration: tool wrapping and registration with `mcp:server:tool` naming."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lovelaice.mcp import _wrap_mcp_tool, _mcp_display_name


def test_mcp_display_name() -> None:
    assert _mcp_display_name("filesystem", "read_file") == "mcp:filesystem:read_file"


@pytest.mark.asyncio
async def test_wrap_mcp_tool_calls_session() -> None:
    """The wrapped tool's run() invokes session.call_tool and returns the text content."""
    session = MagicMock()
    result_msg = MagicMock()
    result_msg.content = [MagicMock(text="hello from mcp")]
    session.call_tool = AsyncMock(return_value=result_msg)

    mcp_tool = MagicMock()
    mcp_tool.name = "read_file"
    mcp_tool.description = "Read a file"
    mcp_tool.inputSchema = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    }

    wrapped = _wrap_mcp_tool(server_name="filesystem", tool=mcp_tool, session=session)
    assert wrapped.name == "mcp:filesystem:read_file"
    assert "Read a file" in wrapped.description

    out = await wrapped.run(path="/tmp/x")
    session.call_tool.assert_awaited_once_with("read_file", {"path": "/tmp/x"})
    assert "hello from mcp" in out
```

- [ ] **Step 2: Run; expect failures.**

Run: `uv run pytest tests/test_mcp.py -v`
Expected: FAIL — `lovelaice.mcp` does not exist.

- [ ] **Step 3: Create `src/lovelaice/mcp.py`.**

```python
"""MCP support: spawn stdio MCP servers and register their tools on the agent.

This is a thin wrapper around the official `mcp` Python SDK. Each tool
exposed by an MCP server becomes a `lingo.tools.Tool` with display name
`mcp:<server>:<tool>` and a JSON-schema-derived parameter map.

Lifecycle: servers spawn at `Config.build()` time and inherit the parent
process lifetime. v1 does not clean them up on exit — the OS reaps the
subprocesses. A future `agent.close()` could do graceful teardown.
"""
from __future__ import annotations

import asyncio
import json
import threading
from typing import Any

from lingo.tools import Tool

# `mcp` SDK imports — kept inside functions where possible so tests can
# stub the wrapping helpers without importing the full SDK.
try:
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
except ImportError:  # pragma: no cover
    ClientSession = None  # type: ignore[assignment]
    stdio_client = None  # type: ignore[assignment]
    StdioServerParameters = None  # type: ignore[assignment]


_PYTHON_TYPE_FROM_JSON: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _mcp_display_name(server: str, tool: str) -> str:
    return f"mcp:{server}:{tool}"


def _params_from_input_schema(schema: dict[str, Any]) -> dict[str, type]:
    """Pluck a `dict[name, python_type]` from a JSON Schema input descriptor."""
    props = (schema or {}).get("properties", {}) or {}
    out: dict[str, type] = {}
    for name, descriptor in props.items():
        json_type = (descriptor or {}).get("type", "string")
        out[name] = _PYTHON_TYPE_FROM_JSON.get(json_type, Any)  # type: ignore[assignment]
    return out


class _MCPTool(Tool):
    """A `lingo.Tool` that proxies to an MCP `session.call_tool` invocation."""

    def __init__(
        self,
        *,
        display_name: str,
        description: str,
        params: dict[str, type],
        session: Any,
        tool_name: str,
    ) -> None:
        super().__init__(display_name, description)
        self._params = params
        self._session = session
        self._tool_name = tool_name

    def parameters(self) -> dict[str, type]:
        return self._params

    async def run(self, **kwargs: Any) -> Any:
        result = await self._session.call_tool(self._tool_name, kwargs)
        # MCP results carry a list of content parts; coerce to text.
        content = getattr(result, "content", None) or []
        parts = []
        for part in content:
            text = getattr(part, "text", None)
            if text is not None:
                parts.append(text)
            else:
                parts.append(json.dumps(getattr(part, "model_dump", lambda: str(part))(), default=str))
        return "\n".join(parts)


def _wrap_mcp_tool(*, server_name: str, tool: Any, session: Any) -> _MCPTool:
    """Wrap one MCP tool definition into a `lingo.Tool`."""
    return _MCPTool(
        display_name=_mcp_display_name(server_name, tool.name),
        description=getattr(tool, "description", "") or "MCP tool",
        params=_params_from_input_schema(getattr(tool, "inputSchema", None) or {}),
        session=session,
        tool_name=tool.name,
    )


def register_mcp_tools(agent: Any, specs: list[dict[str, Any]]) -> None:
    """
    For each spec, spawn the MCP server, fetch its tools, and register
    each on `agent.tools`. Failures on individual servers log + skip.

    Implementation note: MCP sessions live in their own background event
    loop on a dedicated thread. The agent (running on the main loop)
    schedules `call_tool` via `asyncio.run_coroutine_threadsafe`. This
    keeps the lingo loop free of MCP's `async with` lifecycle.
    """
    for spec in specs:
        try:
            session = _start_session_in_background(spec)
            tools = _list_tools_blocking(session)
        except Exception as exc:
            print(f"[mcp] {spec.get('name', '<unnamed>')}: failed to start ({exc!r})")
            continue
        for t in tools:
            wrapped = _wrap_mcp_tool(server_name=spec["name"], tool=t, session=session)
            agent.tools.append(wrapped)


# --- Cross-thread session machinery ----------------------------------------

class _BackgroundSession:
    """Holds an MCP ClientSession alive on a dedicated background loop."""

    def __init__(self, loop: asyncio.AbstractEventLoop, session: Any) -> None:
        self.loop = loop
        self.session = session

    async def call_tool(self, name: str, kwargs: dict[str, Any]) -> Any:
        # Schedule the call on the session's own loop and await the result
        # from whatever loop the caller is on.
        fut = asyncio.run_coroutine_threadsafe(
            self.session.call_tool(name, kwargs),
            self.loop,
        )
        return await asyncio.wrap_future(fut)


def _start_session_in_background(spec: dict[str, Any]) -> _BackgroundSession:
    """Spawn the MCP server, init the session, and keep it alive on a thread."""
    if ClientSession is None or stdio_client is None:
        raise RuntimeError("mcp Python SDK not installed")

    ready = threading.Event()
    holder: dict[str, Any] = {}

    def _runner() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _init_and_park() -> None:
            params = StdioServerParameters(
                command=spec["command"],
                args=spec.get("args", []),
                env=spec.get("env"),
            )
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    holder["session"] = session
                    holder["loop"] = loop
                    ready.set()
                    # Park forever so the context manager stays open.
                    await asyncio.Event().wait()

        try:
            loop.run_until_complete(_init_and_park())
        except Exception as e:
            holder["error"] = e
            ready.set()

    threading.Thread(target=_runner, daemon=True).start()
    ready.wait(timeout=15.0)
    if "error" in holder:
        raise holder["error"]
    return _BackgroundSession(loop=holder["loop"], session=holder["session"])


def _list_tools_blocking(bg: _BackgroundSession) -> list[Any]:
    """Synchronously fetch the tool list from a backgrounded session."""
    fut = asyncio.run_coroutine_threadsafe(bg.session.list_tools(), bg.loop)
    return fut.result(timeout=15.0).tools
```

- [ ] **Step 4: Run mcp tests.**

Run: `uv run pytest tests/test_mcp.py -v`
Expected: 2 PASS. (Tests stub the wrapping helpers; no real MCP server spawned.)

- [ ] **Step 5: Add an integration smoke (optional, skipped by default).**

If `which npx` finds npx and `@modelcontextprotocol/server-everything` is installable, an end-to-end smoke is possible. We do not write one in v1; it is too environment-dependent. Note in the AGENTS.md (Task 19) that real MCP integration requires manual smoke.

- [ ] **Step 6: Commit.**

```bash
git add src/lovelaice/mcp.py tests/test_mcp.py
git commit -m "feat: MCP support — stdio servers in background loop, mcp:server:tool naming"
```

---

### Task 11: Wire `core.py` env block to advertise MCP-loaded tools

**Files:**
- Modify: `src/lovelaice/core.py`
- Test: `tests/test_core_env.py`

`core.Lovelaice.explain_context` already enumerates `self.tools`. Since MCP tools are appended to `agent.tools` in `register_mcp_tools`, the existing iteration already shows them. But the v0.7 hardcoded "YOLO mode" advertisement should mention the workspace root explicitly.

- [ ] **Step 1: Write the failing test.**

Create `tests/test_core_env.py`:

```python
"""The Lovelaice subclass injects an environment-status block each turn."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from lingo import Context, Engine, Message
from unittest.mock import MagicMock

from lovelaice.core import Lovelaice


@pytest.mark.asyncio
async def test_explain_context_mentions_workspace_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    bot = Lovelaice.__new__(Lovelaice)
    bot.skills = []
    bot.tools = []

    ctx = Context([])
    engine = MagicMock()
    await bot.explain_context(ctx, engine)

    last = ctx.messages[-1]
    assert "Workspace root" in str(last.content)
    assert str(tmp_path) in str(last.content)


@pytest.mark.asyncio
async def test_explain_context_lists_mcp_tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    bot = Lovelaice.__new__(Lovelaice)
    bot.skills = []
    fake_tool = MagicMock(); fake_tool.name = "mcp:fs:read"; fake_tool.description = "read a file"
    bot.tools = [fake_tool]

    ctx = Context([])
    engine = MagicMock()
    await bot.explain_context(ctx, engine)

    last_text = str(ctx.messages[-1].content)
    assert "mcp:fs:read" in last_text
    assert "read a file" in last_text
```

- [ ] **Step 2: Run; expect failure.**

Run: `uv run pytest tests/test_core_env.py -v`
Expected: FAIL — current `core.py` says "Working directory:" but not "Workspace root".

- [ ] **Step 3: Replace `src/lovelaice/core.py`.**

```python
from __future__ import annotations

import getpass
import os
from datetime import datetime

from lingo import LLM, Context, Engine, Lingo, Message


class Lovelaice(Lingo):
    """
    The Lovelaice agent: a thin Lingo subclass that injects environment
    awareness into the system prompt before each turn.
    """

    def __init__(self, llm: LLM, prompt: str):
        super().__init__(
            name="Lovelaice",
            description="A local-first coding agent.",
            llm=llm,
            system_prompt=prompt,
        )
        self.before(self.explain_context)

    async def explain_context(self, context: Context, engine: Engine):
        """Prepend a fresh system message describing the current environment.

        Re-emitted on every turn so the agent always sees up-to-date
        capabilities (registered tools, MCP tools, current cwd).
        """
        commands = "\n".join(f"  - {c.name}: {c.description}" for c in self.skills) or "  - (none)"
        tools = "\n".join(f"  - {t.name}: {t.description}" for t in self.tools) or "  - (none)"

        status = f"""
# Environment

- Time: {datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")}
- User: {getpass.getuser()}
- Workspace root (cwd): {os.getcwd()}

# Registered commands

{commands}

# Registered tools

{tools}

You operate in YOLO mode: tool calls execute immediately without
confirmation. Be deliberate about destructive actions (file writes,
shell commands that modify state) — read before you write, and
prefer surgical edits over full rewrites.
""".strip()

        context.append(Message.system(status))
```

- [ ] **Step 4: Run; expect pass.**

Run: `uv run pytest tests/test_core_env.py -v`
Expected: 2 PASS.

- [ ] **Step 5: Commit.**

```bash
git add src/lovelaice/core.py tests/test_core_env.py
git commit -m "refactor(core): env block advertises 'Workspace root (cwd)' explicitly"
```

---

## Phase 4 — One-shot mode

### Task 12: `oneshot.py` — Rich streaming + isatty pipe detection

**Files:**
- Create: `src/lovelaice/oneshot.py`
- Test: `tests/test_oneshot.py`

In one-shot mode we stream the working transcript via Rich `Live`. When stdout is not a tty (piped), we suppress chrome and emit only the final reply on stdout, with optional `--verbose` re-routing the transcript to stderr.

- [ ] **Step 1: Write the failing test.**

Create `tests/test_oneshot.py`:

```python
"""One-shot rendering: tty detection, exit codes, plain-pipe mode."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lovelaice.oneshot import _is_pipe, run_oneshot


def test_is_pipe_returns_true_when_not_tty() -> None:
    fake = MagicMock(); fake.isatty.return_value = False
    assert _is_pipe(fake) is True


def test_is_pipe_returns_false_when_tty() -> None:
    fake = MagicMock(); fake.isatty.return_value = True
    assert _is_pipe(fake) is False


@pytest.mark.asyncio
async def test_run_oneshot_emits_reply_to_stdout_when_piped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """When stdout is not a tty, only the agent's final reply hits stdout."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".lovelaice.py").write_text(
        "from lovelaice import Config\nconfig = Config(models={'default': {'model': 'x'}}, prompt='x')\n"
    )

    fake_bot = MagicMock()
    fake_bot.chat = AsyncMock(return_value=MagicMock(content="final answer"))

    fake_config = MagicMock()
    fake_config.build = MagicMock(return_value=fake_bot)

    with patch("lovelaice.oneshot.load_agent_from_config", return_value=fake_config), \
         patch("lovelaice.oneshot._is_pipe", return_value=True):
        rc = await run_oneshot(Path(".lovelaice.py"), model=None, prompt="hi", verbose=False)

    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out.strip() == "final answer"
    # In pipe mode, we explicitly do not render Rich panels; verify minimal output.
    assert "thinking" not in captured.out.lower()
```

- [ ] **Step 2: Run; expect failure.**

Run: `uv run pytest tests/test_oneshot.py -v`
Expected: FAIL — `lovelaice.oneshot` does not exist.

- [ ] **Step 3: Create `src/lovelaice/oneshot.py`.**

```python
"""One-shot mode: stream the agent's working transcript to stdout via Rich,
or emit just the final reply when stdout is piped.

When --verbose is passed, full tool result bodies are rendered. Without
it, tool calls render as one-line summaries only — the agent's final
reply is the user-facing payload.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import IO, Optional

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel

from .config import load_agent_from_config


def _is_pipe(stream: IO) -> bool:
    """True if `stream` is not connected to a tty."""
    try:
        return not stream.isatty()
    except (AttributeError, ValueError):
        return True


async def run_oneshot(
    config_path: Path,
    *,
    model: Optional[str],
    prompt: str,
    verbose: bool,
) -> int:
    """Execute one agentic turn. Returns the desired process exit code."""
    pipe_mode = _is_pipe(sys.stdout)
    console = Console(stderr=verbose and pipe_mode)  # verbose-pipe → stderr
    quiet = pipe_mode and not verbose

    reply_buffer: list[str] = []
    reasoning_buffer: list[str] = []

    def on_token(t: str) -> None:
        reply_buffer.append(t)

    def on_reasoning_token(t: str) -> None:
        reasoning_buffer.append(t)

    config = load_agent_from_config(config_path)

    try:
        bot = config.build(
            model=model,
            on_token=on_token if not quiet else (lambda _t: None),
            on_reasoning_token=on_reasoning_token if not quiet else (lambda _t: None),
        )
    except Exception as e:
        print(f"Failed to build agent: {e}", file=sys.stderr)
        return 2

    try:
        if quiet:
            # No Live, no panels; just run and print the final reply on stdout.
            result = await bot.chat(prompt)
            print(getattr(result, "content", "") or "", flush=True)
            return 0

        with Live(console=console, refresh_per_second=12, vertical_overflow="visible") as live:
            def render() -> Panel:
                parts = []
                if reasoning_buffer:
                    parts.append(Panel(Markdown("".join(reasoning_buffer)),
                                       title="[dim italic]thinking[/]",
                                       border_style="bright_black",
                                       expand=False))
                parts.append(Panel(Markdown("".join(reply_buffer)),
                                   title="[bold blue]Lovelaice[/]",
                                   border_style="blue",
                                   expand=False))
                return parts[-1] if len(parts) == 1 else _stack(parts)

            async def pump_live() -> None:
                while True:
                    live.update(render())
                    await asyncio.sleep(1 / 12)

            pump_task = asyncio.create_task(pump_live())
            try:
                await bot.chat(prompt)
            finally:
                pump_task.cancel()
                live.update(render())
        return 0
    except asyncio.TimeoutError:
        print("LLM call timed out", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"LLM error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


def _stack(panels: list[Panel]) -> "rich.console.Group":  # type: ignore[name-defined]
    """Stack panels vertically as a Rich Group."""
    from rich.console import Group
    return Group(*panels)
```

- [ ] **Step 4: Run; expect pass.**

Run: `uv run pytest tests/test_oneshot.py -v`
Expected: 3 PASS.

- [ ] **Step 5: Commit.**

```bash
git add src/lovelaice/oneshot.py tests/test_oneshot.py
git commit -m "feat: oneshot.py — Rich Live transcript with pipe-detection (plain stdout when not tty)"
```

---

## Phase 5 — TUI

The TUI work is harder to TDD with high fidelity — Textual's `App.run_test()` exposes a `Pilot` object that drives keypress simulation and snapshot DOM inspection, but full visual fidelity needs a manual smoke. We unit-test the parts that are testable (block models, slash command parser) and use `Pilot` for app-level behavior. UI polish gets a manual smoke checklist at the end.

### Task 13: TUI app skeleton (header / scrolling transcript / input / footer)

**Files:**
- Create: `src/lovelaice/tui/__init__.py` (empty)
- Create: `src/lovelaice/tui/app.py`
- Test: `tests/test_tui_app.py`

- [ ] **Step 1: Create the empty package init.**

`src/lovelaice/tui/__init__.py`:

```python
```

- [ ] **Step 2: Write the failing test.**

Create `tests/test_tui_app.py`:

```python
"""Textual app skeleton smoke tests, driven via App.run_test()."""
from __future__ import annotations

from pathlib import Path

import pytest

from lovelaice.tui.app import LovelaiceApp


@pytest.mark.asyncio
async def test_app_mounts_with_header_transcript_input_footer(workspace_dir: Path) -> None:
    """The app starts up and exposes the four core regions by id."""
    app = LovelaiceApp(config_path=Path(".lovelaice.py"), model=None, _build_agent=lambda *a, **kw: None)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.query_one("#header") is not None
        assert app.query_one("#transcript") is not None
        assert app.query_one("#input") is not None
        assert app.query_one("#footer") is not None


@pytest.mark.asyncio
async def test_app_quits_on_ctrl_d(workspace_dir: Path) -> None:
    app = LovelaiceApp(config_path=Path(".lovelaice.py"), model=None, _build_agent=lambda *a, **kw: None)
    async with app.run_test() as pilot:
        await pilot.press("ctrl+d")
        await pilot.pause()
        assert app._exit  # Textual's internal flag set on exit
```

- [ ] **Step 3: Create `src/lovelaice/tui/app.py`.**

```python
"""Textual full-screen TUI app for lovelaice. Single-pane layout:
header (model + cwd) / transcript (scrolling) / input / footer.

The app holds the agent instance built from the workspace's .lovelaice.py
and dispatches user input to it. Streaming hooks wire `on_token` and
`on_reasoning_token` into the active transcript block.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Optional

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.binding import Binding
from textual.widgets import Header, Footer, Input, RichLog, Static

from .transcript import Transcript


class LovelaiceApp(App):
    """The lovelaice full-screen TUI."""

    CSS_PATH = None
    CSS = """
    Screen { layout: vertical; }
    #header { dock: top; height: 1; background: $boost; color: $text; padding: 0 1; }
    #footer { dock: bottom; height: 1; background: $boost; color: $text-muted; padding: 0 1; }
    #transcript { height: 1fr; }
    #input { dock: bottom; height: auto; }
    """

    BINDINGS = [
        Binding("ctrl+d", "quit", "Quit", show=False),
        Binding("ctrl+c", "cancel_or_quit", "Cancel", show=True),
    ]

    def __init__(
        self,
        config_path: Path,
        model: Optional[str],
        _build_agent: Optional[Callable[..., Any]] = None,
    ) -> None:
        super().__init__()
        self._config_path = config_path
        self._model_arg = model
        # Tests inject a stub builder via _build_agent. Real launches use None.
        self._build_agent = _build_agent
        self._agent: Any = None
        self._last_ctrl_c_t: float = 0.0

    def compose(self) -> ComposeResult:
        yield Static(self._header_text(), id="header")
        with Vertical(id="transcript_container"):
            yield Transcript(id="transcript")
        yield Input(placeholder="Ask lovelaice…", id="input")
        yield Static(self._footer_text(), id="footer")

    def _header_text(self) -> str:
        model = self._model_arg or "default"
        return f"Lovelaice · {model} · {os.getcwd()}"

    def _footer_text(self) -> str:
        return "Enter submit · Shift+Enter newline · Ctrl+C cancel · Ctrl+D exit · /help"

    async def on_mount(self) -> None:
        if self._build_agent is None:
            from ..config import load_agent_from_config
            cfg = load_agent_from_config(self._config_path)
            transcript = self.query_one("#transcript", Transcript)
            self._agent = cfg.build(
                model=self._model_arg,
                on_token=transcript.on_reply_token,
                on_reasoning_token=transcript.on_reasoning_token,
            )
        else:
            self._agent = self._build_agent()

    async def action_cancel_or_quit(self) -> None:
        # Cancellation logic is added in Task 16; the skeleton just exits.
        await self.action_quit()


async def run_tui(config_path: Path, *, model: Optional[str]) -> None:
    """Entrypoint called from cli.py."""
    app = LovelaiceApp(config_path=config_path, model=model)
    await app.run_async()
```

- [ ] **Step 4: Create a stub `transcript.py` that satisfies the import.**

`src/lovelaice/tui/transcript.py`:

```python
"""Scrolling transcript widget for the TUI. Holds message/thinking/tool blocks.
Block model is fleshed out in Task 14; this stub provides just enough surface
for the app skeleton tests to run.
"""
from __future__ import annotations

from textual.widgets import RichLog


class Transcript(RichLog):
    """A vertically scrolling log of conversation blocks."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, highlight=False, markup=True, wrap=True)

    def on_reply_token(self, token: str) -> None:
        # Appended on each LLM token. Real rendering arrives in Task 15.
        pass

    def on_reasoning_token(self, token: str) -> None:
        pass
```

- [ ] **Step 5: Run; expect pass.**

Run: `uv run pytest tests/test_tui_app.py -v`
Expected: 2 PASS.

- [ ] **Step 6: Commit.**

```bash
git add src/lovelaice/tui/ tests/test_tui_app.py
git commit -m "feat(tui): skeleton App with header/transcript/input/footer regions"
```

---

### Task 14: Transcript blocks (message / thinking / tool / error)

**Files:**
- Create: `src/lovelaice/tui/blocks.py`
- Modify: `src/lovelaice/tui/transcript.py`
- Test: `tests/test_tui_blocks.py`

The transcript holds an ordered list of *blocks*. Each block is a `Static` widget rendered as a Rich `Panel`. Blocks support **append** (during streaming) and **finalize** (collapse summary, switch border).

- [ ] **Step 1: Write the failing test.**

Create `tests/test_tui_blocks.py`:

```python
"""Block model tests."""
from __future__ import annotations

from lovelaice.tui.blocks import (
    ErrorBlock, MessageBlock, ReplyBlock, ThinkingBlock, ToolCallBlock,
)


def test_user_message_block_holds_text() -> None:
    b = MessageBlock(role="user", text="hello")
    assert b.role == "user"
    assert b.text == "hello"


def test_reply_block_appends_tokens() -> None:
    b = ReplyBlock()
    b.append("hello ")
    b.append("world")
    assert b.text == "hello world"


def test_thinking_block_collapsed_after_finalize() -> None:
    b = ThinkingBlock()
    b.append("thinking deeply")
    b.finalize()
    assert b.collapsed is True
    assert "thinking deeply" in b.text


def test_tool_call_block_summary_is_one_line() -> None:
    b = ToolCallBlock(tool_name="bash", summary="ran `ls`")
    assert b.summary == "ran `ls`"


def test_error_block_stores_message() -> None:
    b = ErrorBlock("LLM error: connection refused")
    assert "LLM error" in b.message
```

- [ ] **Step 2: Run; expect ImportError.**

Run: `uv run pytest tests/test_tui_blocks.py -v`
Expected: FAIL.

- [ ] **Step 3: Create `src/lovelaice/tui/blocks.py`.**

```python
"""Conversation blocks rendered in the transcript."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class MessageBlock:
    """A user or assistant message rendered in plain text."""
    role: Literal["user", "assistant", "system"]
    text: str = ""

    def append(self, token: str) -> None:
        self.text += token


@dataclass
class ReplyBlock:
    """Streaming agent reply, rendered as a bordered Markdown panel."""
    text: str = ""
    finalized: bool = False

    def append(self, token: str) -> None:
        self.text += token

    def finalize(self) -> None:
        self.finalized = True


@dataclass
class ThinkingBlock:
    """Reasoning tokens, dim/italic, collapsible."""
    text: str = ""
    collapsed: bool = False

    def append(self, token: str) -> None:
        self.text += token

    def finalize(self) -> None:
        self.collapsed = True


@dataclass
class ToolCallBlock:
    """One tool invocation. Summary line stays visible; result body collapses."""
    tool_name: str
    summary: str = ""
    result: str = ""
    error: str | None = None
    collapsed: bool = True


@dataclass
class ErrorBlock:
    """A red banner for LLM transport errors."""
    message: str
```

- [ ] **Step 4: Update `tui/transcript.py` to maintain a block list.**

```python
"""Scrolling transcript widget for the TUI."""
from __future__ import annotations

from typing import Optional

from rich.console import Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static
from textual.containers import VerticalScroll

from .blocks import (
    ErrorBlock, MessageBlock, ReplyBlock, ThinkingBlock, ToolCallBlock,
)


class Transcript(VerticalScroll):
    """Holds an ordered list of conversation blocks and renders them."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.blocks: list = []
        self._current_reply: Optional[ReplyBlock] = None
        self._current_thinking: Optional[ThinkingBlock] = None
        self._sink: Static | None = None

    def on_mount(self) -> None:
        self._sink = Static("", expand=True)
        self.mount(self._sink)

    # --- public API used by the app -----------------------------------

    def add_user_message(self, text: str) -> None:
        self.blocks.append(MessageBlock(role="user", text=text))
        self._refresh()

    def open_thinking_block(self) -> ThinkingBlock:
        b = ThinkingBlock()
        self._current_thinking = b
        self.blocks.append(b)
        return b

    def close_thinking_block(self) -> None:
        if self._current_thinking is not None:
            self._current_thinking.finalize()
            self._current_thinking = None
            self._refresh()

    def open_reply_block(self) -> ReplyBlock:
        b = ReplyBlock()
        self._current_reply = b
        self.blocks.append(b)
        return b

    def close_reply_block(self) -> None:
        if self._current_reply is not None:
            self._current_reply.finalize()
            self._current_reply = None
            self._refresh()

    def add_tool_call(self, tool_name: str, summary: str, result: str = "", error: str | None = None) -> None:
        self.blocks.append(ToolCallBlock(tool_name=tool_name, summary=summary, result=result, error=error))
        self._refresh()

    def add_error(self, message: str) -> None:
        self.blocks.append(ErrorBlock(message=message))
        self._refresh()

    def clear_context_marker(self) -> None:
        self.blocks.append(MessageBlock(role="system", text="── context cleared ──"))
        self._refresh()

    # --- streaming hooks (called from LLM callbacks) ------------------

    def on_reply_token(self, token: str) -> None:
        if self._current_reply is None:
            self.open_reply_block()
        if self._current_thinking is not None:
            self.close_thinking_block()
        assert self._current_reply is not None
        self._current_reply.append(token)
        self._refresh()

    def on_reasoning_token(self, token: str) -> None:
        if self._current_thinking is None:
            self.open_thinking_block()
        assert self._current_thinking is not None
        self._current_thinking.append(token)
        self._refresh()

    # --- rendering ----------------------------------------------------

    def _render_block(self, block) -> Panel | Text:
        if isinstance(block, MessageBlock):
            if block.role == "user":
                return Panel(Text(block.text, style="bold green"), border_style="green", expand=False)
            return Text(block.text, style="dim")
        if isinstance(block, ReplyBlock):
            return Panel(Markdown(block.text or " "), title="[bold blue]Lovelaice[/]",
                         border_style="blue", expand=False)
        if isinstance(block, ThinkingBlock):
            body = Markdown(block.text or " ") if not block.collapsed else Text("(thinking — click to expand)", style="dim italic")
            return Panel(body, title="[dim italic]thinking[/]", border_style="bright_black", expand=False)
        if isinstance(block, ToolCallBlock):
            color = "red" if block.error else "yellow"
            head = f"{block.tool_name}: {block.summary}" + (f"  ✗ {block.error}" if block.error else "")
            return Text(head, style=color)
        if isinstance(block, ErrorBlock):
            return Panel(Text(block.message, style="bold red"), border_style="red", expand=False)
        return Text(repr(block))

    def _refresh(self) -> None:
        if self._sink is None:
            return
        group = Group(*[self._render_block(b) for b in self.blocks])
        self._sink.update(group)
        self.scroll_end(animate=False)
```

- [ ] **Step 5: Run; expect pass.**

Run: `uv run pytest tests/test_tui_blocks.py tests/test_tui_app.py -v`
Expected: 7 PASS.

- [ ] **Step 6: Commit.**

```bash
git add src/lovelaice/tui/blocks.py src/lovelaice/tui/transcript.py tests/test_tui_blocks.py
git commit -m "feat(tui): block model — user/reply/thinking/tool/error, transcript renders them"
```

---

### Task 15: TUI input loop and tool-call observation hooks

**Files:**
- Modify: `src/lovelaice/tui/app.py`
- Modify: `src/lovelaice/core.py` (add hooks for tool start/finish observation)
- Test: `tests/test_tui_input.py`

When the user submits a message:
1. Add a user-message block to the transcript.
2. Disable the input until the agent finishes.
3. Run `agent.chat(user_input)` as a background task with a cancellation handle.
4. Stream tokens via the on_token / on_reasoning_token hooks already wired on the transcript.
5. Render a tool-call block whenever the agent invokes a tool.

For the tool-call rendering, we extend `Lovelaice.before` / `after` hooks: register a hook that opens a `ToolCallBlock` on each `engine.invoke` call. The simplest way is to wrap `engine.invoke` at agent build time. Because lingo's `Engine` is created fresh on each `chat()` call, we instead patch the agent to expose a hook surface.

Pragmatic approach: introduce a `Lovelaice.on_tool_call(...)` callback that the react loop invokes after each `engine.invoke`. Modify `commands/react.py` to call this hook, and wire the TUI to add a `ToolCallBlock` from there.

- [ ] **Step 1: Modify `commands/react.py` to fire a tool callback.**

Replace the loop body to call an optional hook:

```python
async def react(context: Context, engine: Engine, *, max_steps: int = 20) -> None:
    """[docstring unchanged from Task 3]"""
    context.append(Message.system(REACT_HEADER))

    on_tool_call = getattr(engine, "_lovelaice_on_tool_call", None)

    for _ in range(max_steps):
        done = await engine.decide(context, DONE_INSTRUCTION)
        if done:
            break

        tool = await engine.equip(context)
        result = await engine.invoke(context, tool)
        context.append(Message.tool(result.model_dump()))

        if on_tool_call is not None:
            on_tool_call(result)

    final = await engine.reply(
        context,
        "Reply to the user now with a concise summary of what was done and the answer to their request.",
    )
    context.append(final)
```

(Only the `on_tool_call = …` line and the `if on_tool_call …` block are new. Update the existing react.py accordingly.)

- [ ] **Step 2: Modify `Lovelaice.chat` to attach the hook.**

Add to `core.py` (override `chat` from `Lingo`):

```python
    async def chat(self, msg: str) -> Message:
        """Same as Lingo.chat() but attaches `_lovelaice_on_tool_call` to the engine."""
        from lingo import Context
        from lingo.engine import Engine

        self.messages.append(Message.user(msg))
        context = Context(list(self.messages))
        engine = Engine(self.llm, self.tools)
        engine._lovelaice_on_tool_call = getattr(self, "_on_tool_call", None)  # type: ignore[attr-defined]
        flow = self._build_flow()
        await flow.execute(context, engine)
        for m in context.messages[len(self.messages):]:
            self.messages.append(m)
        return self.messages[-1]
```

(The vanilla `Lingo.chat` does the same minus the engine-attribute attach.)

- [ ] **Step 3: Write the failing test for input handling.**

Create `tests/test_tui_input.py`:

```python
"""TUI input loop: submitting a message drives agent.chat and renders blocks."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from lovelaice.tui.app import LovelaiceApp


@pytest.mark.asyncio
async def test_submit_calls_agent_and_renders_user_block(workspace_dir: Path) -> None:
    fake_agent = MagicMock()
    fake_agent.chat = AsyncMock(return_value=MagicMock(content="ok"))

    app = LovelaiceApp(
        config_path=Path(".lovelaice.py"),
        model=None,
        _build_agent=lambda: fake_agent,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#input")
        await pilot.press(*list("hello"))
        await pilot.press("enter")
        await pilot.pause()

        fake_agent.chat.assert_awaited_with("hello")
        transcript = app.query_one("#transcript")
        assert any(getattr(b, "role", None) == "user" and b.text == "hello" for b in transcript.blocks)
```

- [ ] **Step 4: Run; expect failure.**

Run: `uv run pytest tests/test_tui_input.py -v`
Expected: FAIL.

- [ ] **Step 5: Wire `LovelaiceApp` input handling.**

Add to `src/lovelaice/tui/app.py`:

```python
    async def on_input_submitted(self, event) -> None:
        """User pressed Enter."""
        text = event.value.strip()
        if not text:
            return
        input_widget = self.query_one("#input", Input)
        input_widget.value = ""

        if text.startswith("/"):
            await self._handle_slash(text)
            return

        transcript = self.query_one("#transcript", Transcript)
        transcript.add_user_message(text)
        input_widget.disabled = True
        try:
            self._current_turn = self.run_worker(self._run_turn(text), exclusive=True)
        except Exception as e:
            transcript.add_error(f"{type(e).__name__}: {e}")
            input_widget.disabled = False

    async def _run_turn(self, prompt: str) -> None:
        transcript = self.query_one("#transcript", Transcript)

        def on_tool_call(result) -> None:
            transcript.add_tool_call(
                tool_name=result.tool,
                summary=str(result.result)[:80] if result.result else "",
                result=str(result.result or ""),
                error=result.error,
            )

        try:
            self._agent._on_tool_call = on_tool_call  # type: ignore[attr-defined]
            await self._agent.chat(prompt)
            transcript.close_reply_block()
        except Exception as e:
            transcript.add_error(f"{type(e).__name__}: {e}")
        finally:
            self.query_one("#input", Input).disabled = False

    async def _handle_slash(self, text: str) -> None:
        # Slash commands wired in Task 17.
        from .slash import handle_slash
        await handle_slash(self, text)
```

Also add `from textual.widgets import Input` to the existing imports if not present, and keep `from .transcript import Transcript`.

Create a stub `src/lovelaice/tui/slash.py` for Task 17 to fill in:

```python
"""Slash command dispatch. Filled in by Task 17."""
from __future__ import annotations

async def handle_slash(app, text: str) -> None:
    transcript = app.query_one("#transcript")
    transcript.add_error(f"unknown slash command: {text}")
```

- [ ] **Step 6: Run; expect pass.**

Run: `uv run pytest tests/test_tui_input.py -v`
Expected: PASS.

- [ ] **Step 7: Commit.**

```bash
git add src/lovelaice/commands/react.py src/lovelaice/core.py src/lovelaice/tui/app.py src/lovelaice/tui/slash.py tests/test_tui_input.py
git commit -m "feat(tui): input submission drives agent.chat; tool calls render as blocks"
```

---

### Task 16: TUI cancellation (single Ctrl+C cancels turn, double quits)

**Files:**
- Modify: `src/lovelaice/tui/app.py`
- Test: `tests/test_tui_cancel.py`

Behavior: a turn is cancellable. `Ctrl+C` while a turn is running cancels the worker; the transcript appends a red `↳ cancelled by user` line and re-enables input. Two `Ctrl+C` within ~1 second quit the app (whether or not a turn is running).

- [ ] **Step 1: Write the failing test.**

Create `tests/test_tui_cancel.py`:

```python
"""Cancellation: single Ctrl+C aborts the turn; double quits."""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from lovelaice.tui.app import LovelaiceApp


@pytest.mark.asyncio
async def test_single_ctrl_c_cancels_running_turn(workspace_dir: Path) -> None:
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def slow_chat(*a, **kw):
        started.set()
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            cancelled.set()
            raise

    fake_agent = MagicMock()
    fake_agent.chat = slow_chat

    app = LovelaiceApp(
        config_path=Path(".lovelaice.py"),
        model=None,
        _build_agent=lambda: fake_agent,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#input")
        await pilot.press(*list("hi"))
        await pilot.press("enter")
        await asyncio.wait_for(started.wait(), timeout=2.0)
        await pilot.press("ctrl+c")
        await asyncio.wait_for(cancelled.wait(), timeout=2.0)
        assert not app._exit  # single Ctrl+C must NOT quit
```

- [ ] **Step 2: Run; expect failure.**

Run: `uv run pytest tests/test_tui_cancel.py -v`
Expected: FAIL — `action_cancel_or_quit` currently just quits.

- [ ] **Step 3: Implement cancellation.**

Replace `action_cancel_or_quit` in `tui/app.py`:

```python
    async def action_cancel_or_quit(self) -> None:
        import time
        now = time.monotonic()
        if now - self._last_ctrl_c_t < 1.0:
            await self.action_quit()
            return
        self._last_ctrl_c_t = now

        worker = getattr(self, "_current_turn", None)
        if worker is not None and not worker.is_finished:
            worker.cancel()
            transcript = self.query_one("#transcript")
            transcript.add_error("↳ cancelled by user")
            self.query_one("#input").disabled = False
            self._current_turn = None
            return

        # No turn in flight — single Ctrl+C is a no-op (status hint only)
```

- [ ] **Step 4: Run; expect pass.**

Run: `uv run pytest tests/test_tui_cancel.py -v`
Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add src/lovelaice/tui/app.py tests/test_tui_cancel.py
git commit -m "feat(tui): single Ctrl+C cancels current turn; double quits"
```

---

### Task 17: Slash commands (`/help`, `/model`, `/clear`, `/cost`, `/cwd`, `/exit`)

**Files:**
- Modify: `src/lovelaice/tui/slash.py`
- Modify: `src/lovelaice/tui/app.py` (header refresh on `/model`)
- Test: `tests/test_tui_slash.py`

- [ ] **Step 1: Write the failing test.**

Create `tests/test_tui_slash.py`:

```python
"""Slash command tests."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from lovelaice.tui.app import LovelaiceApp


@pytest.mark.asyncio
async def test_slash_cwd_shows_workspace_root(workspace_dir: Path) -> None:
    fake_agent = MagicMock()
    app = LovelaiceApp(config_path=Path(".lovelaice.py"), model=None, _build_agent=lambda: fake_agent)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#input")
        for ch in "/cwd": await pilot.press(ch)
        await pilot.press("enter")
        await pilot.pause()
        transcript = app.query_one("#transcript")
        text_blob = "\n".join(getattr(b, "text", getattr(b, "message", "")) for b in transcript.blocks)
        assert str(workspace_dir) in text_blob


@pytest.mark.asyncio
async def test_slash_clear_resets_messages(workspace_dir: Path) -> None:
    fake_agent = MagicMock()
    fake_agent.messages = ["a", "b"]
    app = LovelaiceApp(config_path=Path(".lovelaice.py"), model=None, _build_agent=lambda: fake_agent)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#input")
        for ch in "/clear": await pilot.press(ch)
        await pilot.press("enter")
        await pilot.pause()
        assert fake_agent.messages == []


@pytest.mark.asyncio
async def test_slash_exit_quits(workspace_dir: Path) -> None:
    fake_agent = MagicMock()
    app = LovelaiceApp(config_path=Path(".lovelaice.py"), model=None, _build_agent=lambda: fake_agent)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#input")
        for ch in "/exit": await pilot.press(ch)
        await pilot.press("enter")
        await pilot.pause()
        assert app._exit
```

- [ ] **Step 2: Run; expect failures.**

Run: `uv run pytest tests/test_tui_slash.py -v`
Expected: FAIL.

- [ ] **Step 3: Replace `tui/slash.py`.**

```python
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
        # Aggregated usage lives on app._cumulative_usage (added below).
        usage = getattr(app, "_cumulative_usage", None)
        if usage is None:
            transcript.add_user_message("No usage recorded yet.")
        else:
            transcript.add_user_message(
                f"prompt_tokens={usage['prompt']}  completion_tokens={usage['completion']}  total={usage['total']}"
            )
        return

    if cmd == "/model":
        models = getattr(app, "_available_models", None) or []
        current = getattr(app, "_active_model", None)
        if not arg:
            lines = [f"  {'* ' if m == current else '  '}{m}" for m in models]
            transcript.add_user_message("Models:\n" + "\n".join(lines))
            return
        if arg not in models:
            transcript.add_error(f"unknown model alias: {arg!r}")
            return
        app._active_model = arg
        app.query_one("#header").update(app._header_text())
        transcript.add_user_message(f"switched to {arg} for next turn")
        return

    transcript.add_error(f"unknown slash command: {cmd}")
```

- [ ] **Step 4: Wire app state for `/cost` and `/model`.**

In `tui/app.py` `__init__`, add:

```python
        self._cumulative_usage = {"prompt": 0, "completion": 0, "total": 0}
        self._available_models: list[str] = []
        self._active_model: str | None = None
```

In `on_mount` (the real-launch branch), after `cfg = load_agent_from_config(self._config_path)`:

```python
            self._available_models = list(cfg.models.keys())
            self._active_model = self._model_arg or cfg.default_model
```

In `_run_turn`, after `await self._agent.chat(prompt)`:

```python
            usage = getattr(self._agent.messages[-1], "usage", None)
            if usage is not None:
                self._cumulative_usage["prompt"] += usage.prompt_tokens
                self._cumulative_usage["completion"] += usage.completion_tokens
                self._cumulative_usage["total"] += usage.total_tokens
```

Update `_header_text` to use `_active_model` when set:

```python
    def _header_text(self) -> str:
        model = getattr(self, "_active_model", None) or self._model_arg or "default"
        return f"Lovelaice · {model} · {os.getcwd()}"
```

- [ ] **Step 5: Run; expect pass.**

Run: `uv run pytest tests/test_tui_slash.py -v`
Expected: 3 PASS.

- [ ] **Step 6: Commit.**

```bash
git add src/lovelaice/tui/slash.py src/lovelaice/tui/app.py tests/test_tui_slash.py
git commit -m "feat(tui): slash commands /help /model /clear /cost /cwd /exit"
```

---

## Phase 6 — Final wiring

### Task 18: Replace `template.py` for the v1 `--init` template

**Files:**
- Modify: `src/lovelaice/template.py`
- Test: `tests/test_template_init.py`

- [ ] **Step 1: Write the failing test.**

Create `tests/test_template_init.py`:

```python
"""`lovelaice --init` writes a working .lovelaice.py."""
from __future__ import annotations

import inspect
from pathlib import Path

from lovelaice import template


def test_template_renders_with_substitutions() -> None:
    src = inspect.getsource(template)
    assert "<default_model>" in src
    assert "<base_url>" in src
    assert "OPENROUTER_API_KEY" in src
    assert "config.tool(list_, name=\"list\")" in src
    assert "from lovelaice.tools import bash, read, write, edit, list_, glob, grep, fetch" in src
    assert "from lovelaice.commands import react" in src
```

- [ ] **Step 2: Run; expect failure.**

Run: `uv run pytest tests/test_template_init.py -v`
Expected: FAIL — current template uses `API_KEY` and v0.4-era tool list.

- [ ] **Step 3: Replace `src/lovelaice/template.py`.**

```python
import os

from lovelaice import Config

# --- Models ---------------------------------------------------------------
# All models go through OpenRouter. The first entry is the default; pick
# another at runtime with `--model <alias>` (one-shot) or `/model` (TUI).
# Add `thinking="low"|"medium"|"high"` (or an int token budget) on a model
# entry to opt into reasoning passthrough.
MODELS = {
    "default": {
        "model": "<default_model>",
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "base_url": "<base_url>",
    },
    # Example: a reasoning-enabled alias
    # "deep": {
    #     "model": "anthropic/claude-sonnet-4-5",
    #     "api_key": os.getenv("OPENROUTER_API_KEY"),
    #     "base_url": "https://openrouter.ai/api/v1",
    #     "thinking": "high",
    # },
}

# --- System prompt --------------------------------------------------------
PROMPT = """
You are Lovelaice, a sovereign coding agent that runs in the user's terminal.
Be concise and act decisively. When a task is ambiguous, ask one focused
question instead of guessing. Prefer surgical edits over full rewrites.
""".strip()

# --- Build the config -----------------------------------------------------
config = Config(
    models=MODELS,
    prompt=PROMPT,
    # mcp=[{"name": "...", "command": "...", "args": [...]}],
)

# --- Default tools --------------------------------------------------------
from lovelaice.tools import bash, read, write, edit, list_, glob, grep, fetch

config.tool(bash)
config.tool(read)
config.tool(write)
config.tool(edit)
config.tool(list_, name="list")
config.tool(glob)
config.tool(grep)
config.tool(fetch)

# --- Default command: ReAct loop ------------------------------------------
from lovelaice.commands import react

config.command(react)

# --- Custom tools and commands --------------------------------------------
# @config.tool
# async def search_notes(query: str) -> str:
#     """Search the user's notes for the given query."""
#     ...
```

- [ ] **Step 4: Update `cli.py::_do_init` to default to OpenRouter.**

Replace `_do_init` so the API URL default reflects OpenRouter:

```python
def _do_init() -> None:
    config_path = Path(".lovelaice.py")
    if config_path.exists():
        typer.echo(f"{config_path} already exists.", err=True)
        raise typer.Exit(code=1)

    default_model = typer.prompt("Default model name", default="google/gemini-2.5-flash")
    base_url = typer.prompt("OpenRouter API base URL", default="https://openrouter.ai/api/v1")

    from lovelaice import template
    source = inspect.getsource(template)
    formatted = source.replace("<default_model>", default_model).replace("<base_url>", base_url)
    config_path.write_text(formatted)
    typer.echo(f"Wrote {config_path} (default model: {default_model}).")
    typer.echo("Set OPENROUTER_API_KEY in your environment before running lovelaice.")
```

- [ ] **Step 5: Run; expect pass.**

Run: `uv run pytest tests/test_template_init.py -v`
Expected: PASS.

- [ ] **Step 6: Commit.**

```bash
git add src/lovelaice/template.py src/lovelaice/cli.py tests/test_template_init.py
git commit -m "feat: v1 --init template (OpenRouter default, full tool set, name='list')"
```

---

### Task 19: Update README for v1 + seed `AGENTS.md`

**Files:**
- Modify: `README.md`
- Create: `AGENTS.md`
- Create: `know-how/writing-a-command.md`
- Create: `know-how/writing-a-tool.md`

The current README describes v0.4-era behavior (`--complete`, `--complete-files`, etc.) — it actively misleads users about v1.

- [ ] **Step 1: Replace `README.md` with a v1-accurate description.**

```markdown
# Lovelaice

A sovereign, local-first coding agent for the terminal. Single ReAct
loop over a small built-in tool set, yolo by default. Two modes:

- **Interactive** — full-screen Textual TUI: `lovelaice`
- **One-shot**   — streams to stdout and exits: `lovelaice <prompt>`

## Install

```bash
pipx install lovelaice
```

## Configure

`lovelaice --init` writes a `.lovelaice.py` in the current directory.
This file *grounds the workspace*: when you run `lovelaice` from any
subdirectory, it walks up to the nearest `.lovelaice.py` and `chdir`s
to its directory before running. Exactly one config grounds the
workspace — there is no stacking.

Set `OPENROUTER_API_KEY` in your environment before running.

```bash
export OPENROUTER_API_KEY=sk-or-...
lovelaice
```

## Commands and tools

The `.lovelaice.py` registers tools and commands as decorators on a
`Config` object. Built-in tools: `bash`, `read`, `write`, `edit`,
`list`, `glob`, `grep`, `fetch`. Add your own with `@config.tool`. See
`know-how/writing-a-tool.md` and `know-how/writing-a-command.md`.

## Thinking mode

Add `thinking="high"` (or `"low"`/`"medium"`, or an integer token
budget) on a model entry to enable OpenRouter's reasoning passthrough.
Reasoning chunks render in a separate dim-italic panel above the
agent's reply.

## MCP

Pass `mcp=[...]` to `Config(...)` to spawn stdio MCP servers and
register their tools. Tool names are prefixed `mcp:<server>:<tool>`.

## License

MIT.
```

- [ ] **Step 2: Create `AGENTS.md`.**

```markdown
# AGENTS.md — lovelaice

A sovereign, local-first terminal coding agent. Single ReAct loop on
top of `lingo`, with a Textual TUI for interactive mode and a Rich-
streamed one-shot mode.

## Quick orientation

- `src/lovelaice/cli.py` — typer entrypoint. Resolves the workspace
  root (chdir to the nearest ancestor `.lovelaice.py`) and dispatches
  to either `oneshot.py` (one-shot) or `tui/app.py` (interactive).
- `src/lovelaice/config.py` — `Config` plugin registry. Loaded by
  evaluating the user's `.lovelaice.py`.
- `src/lovelaice/core.py` — `Lovelaice(Lingo)` injects the env-status
  block on every turn.
- `src/lovelaice/thinking.py` — `ThinkingLLM` adds OpenRouter
  reasoning passthrough on top of `lingo.LLM`.
- `src/lovelaice/mcp.py` — spawns stdio MCP servers in a background
  loop and wraps their tools as `lingo.Tool`s.
- `src/lovelaice/commands/react.py` — the default command (decide /
  equip / invoke loop).
- `src/lovelaice/tools/` — built-in tools.
- `src/lovelaice/tui/` — Textual app, transcript widget, blocks.
- `src/lovelaice/oneshot.py` — Rich-driven one-shot mode.

## Running tests

```bash
uv run pytest
```

## Know-how

Specific procedure docs in `know-how/`. Match the task; load the doc.

- **writing-a-tool** — when adding a new built-in or custom tool.
- **writing-a-command** — when adding an agent-side workflow command.

## Manual smoke checklist

The TUI is hard to fully unit-test. Before tagging a release, manually
smoke:

- `lovelaice --init` in an empty dir → produces a working `.lovelaice.py`.
- `lovelaice "list the files"` (with `OPENROUTER_API_KEY` set) → tool
  call rendered, final reply streams in a Rich panel.
- `echo nothing | lovelaice "list the files" | wc -l` → only the final
  reply on stdout (pipe mode).
- `lovelaice` (no arg) → TUI launches; `/help` shows help; submit a
  message; `Ctrl+C` cancels; `/exit` quits.
- A `.lovelaice.py` with a `thinking="high"` model alias → the
  thinking panel renders during streaming.
```

- [ ] **Step 3: Create `know-how/writing-a-tool.md`.**

```markdown
# Writing a tool

A tool is an async (or sync) Python function decorated with
`@config.tool`. The function's docstring becomes the description the
LLM sees; its annotated parameters become the parameter schema.

## Conventions

- **Async** preferred. Sync functions are auto-wrapped, but the
  agent loop runs async, so async is more direct.
- **Docstring is the prompt.** The LLM picks tools by reading the
  docstring; write it as if you are explaining to the model when to
  use this tool, not to a human reading source.
- **Return text.** Tool results are stringified and concatenated into
  the context as `tool`-role messages. Return a string (or a value
  that stringifies usefully); avoid huge blobs.
- **Workspace-rooted paths.** Cwd is the workspace root; relative
  paths are correct.
- **Display-name override.** Use `config.tool(my_func, name="x")` if
  the function name conflicts with a Python builtin (e.g., `list`).
- **Errors.** Raise normally. The loop catches exceptions and feeds
  them back as a `tool failed` observation.

## Example

```python
@config.tool
async def search_notes(query: str) -> str:
    """Search the user's notes (Obsidian vault) for `query`. Returns
    matching note paths and surrounding context, one match per line."""
    ...
```
```

- [ ] **Step 4: Create `know-how/writing-a-command.md`.**

```markdown
# Writing a command

A command is an `async def(context, engine)` workflow registered with
`@config.command`. It runs as a `lingo` skill: the agent dispatches to
it on user input. The default `react` command (in
`src/lovelaice/commands/react.py`) is a good template.

## Building blocks

`engine` exposes:

- `engine.decide(context, prompt)` — yes/no decision.
- `engine.choose(context, options, prompt)` — pick from a list.
- `engine.equip(context)` — pick a tool from the registered set.
- `engine.invoke(context, tool)` — run the chosen tool with LLM-filled params.
- `engine.reply(context, *instructions)` — generate a final assistant message.
- `engine.create(context, model_cls, *instructions)` — structured output.

`context.append(message)` adds a message; `context.messages` is the
full transcript so far.

## Pattern: a planner-then-act command

```python
@config.command
async def plan_then_execute(context, engine):
    """Produce a step-by-step plan, then execute it."""
    plan = await engine.reply(context, "First, sketch a numbered plan. Do not act yet.")
    context.append(plan)
    # … iterate equip/invoke as in react …
    final = await engine.reply(context, "Summarize what was done.")
    context.append(final)
```

## Anti-patterns

- Calling `engine.act` — that does not exist on `Engine`. Use
  `equip(...)` then `invoke(...)`.
- Assembling tool results with `Message.system(...)` — use
  `Message.tool(result.model_dump())` so the role is correct.
- Adding side effects to `before` hooks that the model can see — they
  go into the system prompt and bloat context.
```

- [ ] **Step 5: Run the full suite to confirm no regressions.**

Run: `uv run pytest -v`
Expected: all PASS.

- [ ] **Step 6: Commit.**

```bash
git add README.md AGENTS.md know-how/
git commit -m "docs: v1 README, AGENTS.md, know-how/{writing-a-tool,writing-a-command}"
```

---

### Task 20: Final manual smoke + version stamp

**Files:**
- Modify: `pyproject.toml` (already at 1.0.0 from Task 1)
- Modify: `src/lovelaice/__init__.py`

- [ ] **Step 1: Confirm `__init__.py` exports.**

Replace `src/lovelaice/__init__.py`:

```python
"""Lovelaice — a sovereign coding agent for the terminal."""
from .config import Config

__version__ = "1.0.0"
__all__ = ["Config", "__version__"]
```

- [ ] **Step 2: Run the full test suite.**

Run: `uv run pytest -v`
Expected: ALL PASS.

- [ ] **Step 3: Manual smoke checklist (from AGENTS.md).**

The engineer (or a human) walks through these against a real
OpenRouter key:

1. `cd /tmp && mkdir lovelaice-smoke && cd lovelaice-smoke`
2. `lovelaice --init` — answer the prompts.
3. `OPENROUTER_API_KEY=... lovelaice "list the files in this directory"` — tool call renders, reply streams.
4. `OPENROUTER_API_KEY=... lovelaice "say hi" | head -1` — only the reply hits stdout.
5. `OPENROUTER_API_KEY=... lovelaice` — TUI launches; type a message, hit Enter; type `/help`; type `/exit`.
6. Edit `.lovelaice.py` to add `thinking="high"` on the default model; rerun. Thinking panel should appear during streaming.

If any of these fail, file a follow-up issue; do not commit a half-working v1.

- [ ] **Step 4: Commit version + tag.**

```bash
git add src/lovelaice/__init__.py
git commit -m "chore: stamp v1.0.0"
git tag v1.0.0
```

(Pushing the tag is the user's call.)

---

## Self-review checklist (run after writing the plan)

- **Spec coverage.** Each spec section maps to one or more tasks:
  - §1 Workspace grounding → Task 2.
  - §2 TUI → Tasks 13–17.
  - §3 One-shot → Task 12.
  - §4 Thinking → Task 9.
  - §5 Tool surface (built-ins, MCP) → Tasks 4–7, 10, 11; Config wiring in 8.
  - §6 Slash commands + lifecycle → Tasks 16, 17.
  - §7 Template → Task 18.
  - §8 Module layout → distributed across Tasks 12 (oneshot.py), 9 (thinking.py), 10 (mcp.py), 13–15 (tui/), 6 (tools/search.py), 7 (tools/web.py), 4 (tools/bash.py), 5 (tools/files.py rename).
  - §9 Open implementation questions — resolved during plan authoring (lingo source inspection): the `engine.act` bug is fixed in Task 3; `delta.reasoning` requires subclass + chat() override per Task 9; MCP runs in a background loop per Task 10; `/cost` reads `usage` from the final stream chunk per Task 17.
- **Type / name consistency.** `_on_tool_call` (Task 15) is set in `_run_turn` and read in `core.Lovelaice.chat` (Task 15) and forwarded into `commands/react.py` via `engine._lovelaice_on_tool_call`. The chain is consistent across files.
- **Placeholders.** None remain.

---

## Out of scope (v1.x and beyond)

- `think` tool for non-reasoning models.
- Session persistence and resume.
- Context compaction / summarization.
- HTTP/SSE MCP transport.
- Multi-provider thinking translation.
- `--json` mode.
- Light theme.
- Dollar-cost accounting in `/cost`.
- Mouse-driven block expand/collapse polish.
