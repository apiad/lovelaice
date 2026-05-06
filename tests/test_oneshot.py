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
        "from lovelaice import Config\n"
        "config = Config(models={'default': {'model': 'x'}}, prompt='x')\n"
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
