"""A report that cannot be delivered is never a traceback and never a silent success.

Three ways standard output fails: the reader of a pipe went away (`burnish critic . | head -3`), standard output is closed, and
the device is full. Each is run for every command that prints, against a real process, with Python's output both buffered
(what CI and a pipe give) and unbuffered (PYTHONUNBUFFERED, which moves the failure from the flush at exit to the first print).
No test points anything at a device node except as a child's own stdout, opened for writing and never replaced.
"""

import errno
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from burnish import cli
from burnish.criteria import CRITERIA

GOOD_PYTHON = '"""A module."""\n\n\ndef add(a: int, b: int) -> int:\n    """Add."""\n    return a + b\n'
README = "# demo\n\nA small demo.\n\n## Install\n\n    pip install demo\n"

#: Every command that prints, with its arguments after the tree path (None: it takes no path).
COMMANDS: dict[str, list[str]] = {
    "check": ["check", "{tree}"],
    "critic": ["critic", "{tree}"],
    "readme-critic": ["readme-critic", "{tree}", "--tier", "over-the-top"],
    "inspect": ["inspect", "{tree}"],
    "readme": ["readme", "{tree}"],
    "finish": ["finish", "{tree}"],
    "cns": ["cns", "{tree}"],
    "criteria": ["criteria"],
    "languages": ["languages"],
}
#: The commands whose run on the test tree earns 0, so a lost report must not be allowed to leave it at 0.
EARNS_ZERO = ["inspect", "readme", "finish", "cns", "criteria", "languages"]

posix_only = pytest.mark.skipif(os.name != "posix", reason="needs POSIX pipes and file descriptors")


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """A folder with a clean module, a module with a finding, and a README, so every command has something to print."""
    root = tmp_path / "tree"
    root.mkdir()
    (root / "ok.py").write_text(GOOD_PYTHON, encoding="utf-8")
    (root / "bad.py").write_text("from os import *\n", encoding="utf-8")
    (root / "README.md").write_text(README, encoding="utf-8")
    return root


def _argv(command: str, tree: Path) -> list[str]:
    return [part.format(tree=tree) for part in COMMANDS[command]]


# ---- in process: a stream that fails the way a pipe or a full disk does

class _Refusing:
    """A stdout whose write (or, for a buffered stream, whose flush) raises."""

    def __init__(self, error: Exception, *, on_write: bool = True) -> None:
        self.error, self.on_write = error, on_write

    def write(self, text: str) -> int:
        if self.on_write:
            raise self.error
        return len(text)

    def flush(self) -> None:
        raise self.error


GONE = BrokenPipeError(errno.EPIPE, "Broken pipe")
FULL = OSError(errno.ENOSPC, "No space left on device")


def _earned(tree: Path, command: str, capsys: pytest.CaptureFixture[str]) -> int:
    code = cli.main(_argv(command, tree))
    capsys.readouterr()
    return code


@pytest.mark.parametrize("on_write", [True, False], ids=["write", "flush"])
@pytest.mark.parametrize("command", list(COMMANDS))
def test_a_reader_that_left_keeps_the_exit_code_the_check_earned(command: str, on_write: bool, tree: Path,
                                                                 capsys: pytest.CaptureFixture[str],
                                                                 monkeypatch: pytest.MonkeyPatch):
    earned = _earned(tree, command, capsys)
    monkeypatch.setattr(sys, "stdout", _Refusing(GONE, on_write=on_write))
    assert cli.main(_argv(command, tree)) == earned
    err = capsys.readouterr().err
    assert "broken pipe" in err and "Traceback" not in err
    assert err.count("went away") == 1


@pytest.mark.parametrize("on_write", [True, False], ids=["write", "flush"])
@pytest.mark.parametrize("command", EARNS_ZERO)
def test_a_full_device_cannot_leave_a_lost_report_at_exit_0(command: str, on_write: bool, tree: Path,
                                                            capsys: pytest.CaptureFixture[str],
                                                            monkeypatch: pytest.MonkeyPatch):
    assert _earned(tree, command, capsys) == cli.EXIT_OK
    monkeypatch.setattr(sys, "stdout", _Refusing(FULL, on_write=on_write))
    assert cli.main(_argv(command, tree)) == cli.EXIT_NOT_DELIVERED
    err = capsys.readouterr().err
    assert "could not write the report to standard output: No space left on device" in err


@pytest.mark.parametrize("command", EARNS_ZERO)
def test_a_closed_standard_output_cannot_leave_a_lost_report_at_exit_0(command: str, tree: Path,
                                                                       capsys: pytest.CaptureFixture[str],
                                                                       monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sys, "stdout", None)   # what Python sets when file descriptor 1 is closed at start
    assert cli.main(_argv(command, tree)) == cli.EXIT_NOT_DELIVERED
    assert "standard output is closed" in capsys.readouterr().err


def test_a_stream_closed_under_us_is_a_delivery_failure_too(tree: Path, capsys: pytest.CaptureFixture[str],
                                                            monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sys, "stdout", _Refusing(ValueError("I/O operation on closed file")))
    assert cli.main(_argv("criteria", tree)) == cli.EXIT_NOT_DELIVERED
    assert "closed file" in capsys.readouterr().err


def test_an_earned_finding_is_kept_when_the_device_is_full(tree: Path, capsys: pytest.CaptureFixture[str],
                                                           monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sys, "stdout", _Refusing(FULL))
    assert cli.main(["check", str(tree)]) == cli.EXIT_FINDINGS
    err = capsys.readouterr().err
    assert "No space left on device" in err and "2 finding(s)" in err   # the summary on stderr is still written


def test_an_earned_cannot_run_is_kept_and_prints_nothing_to_lose(tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                                                 monkeypatch: pytest.MonkeyPatch):
    absent = tmp_path / "absent"
    assert not absent.exists()
    monkeypatch.setattr(sys, "stdout", None)
    assert cli.main(["check", str(absent)]) == cli.EXIT_CANNOT_RUN
    assert "no such file or directory" in capsys.readouterr().err


def test_a_command_with_nothing_to_print_does_not_need_standard_output(tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                                                       monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "ok.py").write_text(GOOD_PYTHON, encoding="utf-8")
    monkeypatch.setattr(sys, "stdout", None)
    assert cli.main(["check", str(tmp_path)]) == cli.EXIT_OK   # no finding, so no line was lost
    assert "standard output" not in capsys.readouterr().err


@pytest.mark.parametrize("flag", ["--version", "--help"])
def test_version_and_help_get_the_same_treatment(flag: str, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sys, "stdout", _Refusing(GONE))
    with pytest.raises(SystemExit) as stopped:
        cli.main([flag])
    assert stopped.value.code == 0
    assert "broken pipe" in capsys.readouterr().err
    monkeypatch.setattr(sys, "stdout", _Refusing(FULL))
    with pytest.raises(SystemExit) as stopped:
        cli.main([flag])
    assert stopped.value.code == cli.EXIT_NOT_DELIVERED


def test_a_report_that_is_delivered_is_delivered_whole(tree: Path, capsys: pytest.CaptureFixture[str]):
    assert cli.main(["criteria"]) == 0
    out = capsys.readouterr().out
    assert out.endswith("\n") and len(out.splitlines()) == len(CRITERIA)


# ---- a real process: a closed pipe, a closed descriptor, a full device

def _env(unbuffered: bool) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONUNBUFFERED"}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if unbuffered:
        env["PYTHONUNBUFFERED"] = "1"
    return env


def _run(argv: list[str], unbuffered: bool, **streams: Any) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run([sys.executable, "-m", "burnish.cli", *argv], stderr=subprocess.PIPE, env=_env(unbuffered),
                          timeout=120, check=False, **streams)


def _earned_by_a_real_run(argv: list[str], unbuffered: bool) -> int:
    return _run(argv, unbuffered, stdout=subprocess.PIPE).returncode


def _delivery_lines(stderr: bytes) -> list[str]:
    return [line for line in stderr.decode().splitlines() if "standard output" in line]


@pytest.fixture(params=[False, True], ids=["buffered", "unbuffered"])
def unbuffered(request: pytest.FixtureRequest) -> bool:
    return bool(request.param)


@posix_only
@pytest.mark.parametrize("command", list(COMMANDS))
def test_a_closed_pipe_is_not_a_traceback_and_keeps_the_earned_code(command: str, tree: Path, unbuffered: bool):
    argv = _argv(command, tree)
    earned = _earned_by_a_real_run(argv, unbuffered)
    assert earned in (0, 1)
    read_end, write_end = os.pipe()
    os.close(read_end)   # the reader left before the command printed anything
    try:
        done = _run(argv, unbuffered, stdout=write_end)
    finally:
        os.close(write_end)
    stderr = done.stderr.decode()
    assert "Traceback" not in stderr and "Exception ignored" not in stderr, stderr
    assert done.returncode == earned, stderr
    assert len(_delivery_lines(done.stderr)) == 1 and "broken pipe" in stderr


@posix_only
@pytest.mark.parametrize("command", list(COMMANDS))
def test_a_closed_standard_output_is_reported_and_never_exits_0(command: str, tree: Path, unbuffered: bool):
    argv = _argv(command, tree)
    earned = _earned_by_a_real_run(argv, unbuffered)
    done = _run(argv, unbuffered, stdout=subprocess.DEVNULL, preexec_fn=lambda: os.close(1))   # fd 1 is closed in the child
    stderr = done.stderr.decode()
    assert "Traceback" not in stderr, stderr
    assert done.returncode == (earned or cli.EXIT_NOT_DELIVERED), stderr
    assert len(_delivery_lines(done.stderr)) == 1 and "standard output is closed" in stderr


@posix_only
@pytest.mark.skipif(not os.path.exists("/dev/full"), reason="needs /dev/full")
@pytest.mark.parametrize("command", list(COMMANDS))
def test_a_full_device_is_reported_and_never_exits_0(command: str, tree: Path, unbuffered: bool):
    argv = _argv(command, tree)
    earned = _earned_by_a_real_run(argv, unbuffered)
    with open("/dev/full", "wb") as full:   # opened for writing as the child's stdout; nothing is ever replaced
        done = _run(argv, unbuffered, stdout=full)
    stderr = done.stderr.decode()
    assert "Traceback" not in stderr and "Exception ignored" not in stderr, stderr
    assert done.returncode == (earned or cli.EXIT_NOT_DELIVERED), stderr
    assert len(_delivery_lines(done.stderr)) == 1 and "No space left on device" in stderr


@posix_only
def test_version_through_a_closed_pipe_is_not_a_traceback(unbuffered: bool):
    read_end, write_end = os.pipe()
    os.close(read_end)
    try:
        done = _run(["--version"], unbuffered, stdout=write_end)
    finally:
        os.close(write_end)
    assert done.returncode == 0 and "Traceback" not in done.stderr.decode()
