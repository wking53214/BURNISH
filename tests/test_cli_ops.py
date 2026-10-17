"""The exit-code table in the README is the code's table, and logging goes to stderr at the level asked for."""

import re
from pathlib import Path

import pytest

from burnish import cli

ROOT = Path(__file__).resolve().parent.parent
GOOD_PYTHON = '"""A module."""\n\n\ndef add(a: int, b: int) -> int:\n    """Add."""\n    return a + b\n'


def _tree(root: Path) -> None:
    (root / "ok.py").write_text(GOOD_PYTHON, encoding="utf-8")


def test_the_readme_exit_code_table_matches_the_code():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    rows = {int(m.group(1)): m.group(2).strip() for m in re.finditer(r"^\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*$", readme, re.M)}
    assert rows == cli.EXIT_CODES


def test_the_module_docstring_lists_the_same_codes():
    for code in cli.EXIT_CODES:
        assert re.search(rf"^\s+{code}\s+\S", cli.__doc__ or "", re.M), f"exit code {code} missing from the cli docstring"


def test_every_documented_code_is_returned_by_some_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    _tree(tmp_path)
    seen = {cli.main(["check", str(tmp_path)])}
    (tmp_path / "bad.py").write_text("from os import *\n", encoding="utf-8")
    seen.add(cli.main(["check", str(tmp_path)]))
    seen.add(cli.main(["check", str(tmp_path / "missing")]))
    capsys.readouterr()
    assert seen == set(cli.EXIT_CODES)


def test_warnings_only_by_default(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("BURNISH_LOG_LEVEL", raising=False)
    _tree(tmp_path)
    assert cli.main(["check", str(tmp_path)]) == 0
    err = capsys.readouterr().err
    assert "DEBUG" not in err and "INFO" not in err


@pytest.mark.parametrize("argv", [["--verbose", "check", "{p}"], ["check", "{p}", "--verbose"], ["-v", "check", "{p}"]])
def test_verbose_shows_the_debug_trail_on_stderr(argv: list[str], tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                                 monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("BURNISH_LOG_LEVEL", raising=False)
    _tree(tmp_path)
    assert cli.main([a.format(p=tmp_path) for a in argv]) == 0
    captured = capsys.readouterr()
    assert "burnish: DEBUG: command=check" in captured.err and "exit code 0" in captured.err
    assert "DEBUG" not in captured.out


def test_the_environment_sets_the_level(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    _tree(tmp_path)
    monkeypatch.setenv("BURNISH_LOG_LEVEL", "info")
    assert cli.main(["check", str(tmp_path)]) == 0
    err = capsys.readouterr().err
    assert "burnish: INFO: exit code 0" in err and "DEBUG" not in err


def test_an_unknown_level_in_the_environment_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                                     monkeypatch: pytest.MonkeyPatch):
    _tree(tmp_path)
    monkeypatch.setenv("BURNISH_LOG_LEVEL", "loud")
    assert cli.main(["check", str(tmp_path)]) == 2
    assert "BURNISH_LOG_LEVEL" in capsys.readouterr().err


def test_logging_does_not_pile_up_handlers_across_runs(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    _tree(tmp_path)
    for _ in range(3):
        cli.main(["-v", "check", str(tmp_path)])
    assert len(cli.log.handlers) == 1
    capsys.readouterr()
