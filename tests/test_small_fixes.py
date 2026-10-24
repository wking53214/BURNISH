"""Round-6 audit, the smaller items: a label, a stream left behind, a file nested too deeply, a link not followed."""

import sys
from pathlib import Path

import pytest

from burnish import cli
from burnish.checks import check_source
from burnish.critic import PoetryCritic

#: A file whose expression nests far deeper than the parser's stack: an unbroken run of unary minus signs.
DEEP = "x = " + "-" * 200_000 + "1\n"


# ---- the critic's heading says what it is

def test_the_critic_heading_names_the_claims_critic_not_poetry(tmp_path: Path):
    (tmp_path / "README.md").write_text("# demo\n", encoding="utf-8")
    (tmp_path / "m.py").write_text('"""m."""\n', encoding="utf-8")
    heading = PoetryCritic().critique(tmp_path).as_markdown().splitlines()[0]
    assert heading == f"# Claims critic: {tmp_path.name}"


# ---- main() leaves standard output as it found it

class _Gone:
    def write(self, text: str) -> int:
        raise BrokenPipeError(32, "Broken pipe")

    def flush(self) -> None:
        raise BrokenPipeError(32, "Broken pipe")


def test_main_puts_standard_output_back_after_a_reader_left(monkeypatch: pytest.MonkeyPatch):
    gone = _Gone()
    monkeypatch.setattr(sys, "stdout", gone)
    assert cli.main(["criteria"]) == cli.EXIT_OK
    assert sys.stdout is gone, "an in-process caller must not find standard output replaced"


def test_main_leaves_a_closed_standard_output_closed_and_does_not_invent_one(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sys, "stdout", None)
    assert cli.main(["criteria"]) == cli.EXIT_NOT_DELIVERED
    assert sys.stdout is None


def test_main_puts_standard_output_back_after_a_failed_write_too(monkeypatch: pytest.MonkeyPatch):
    class Full(_Gone):
        def write(self, text: str) -> int:
            raise OSError(28, "No space left on device")

        def flush(self) -> None:
            raise OSError(28, "No space left on device")

    full = Full()
    monkeypatch.setattr(sys, "stdout", full)
    assert cli.main(["languages"]) == cli.EXIT_NOT_DELIVERED
    assert sys.stdout is full


def test_the_process_entry_point_still_neutralises_a_dead_stream_for_the_flush_at_exit(monkeypatch: pytest.MonkeyPatch):
    """`run` is what the console script and `python -m burnish.cli` call: the interpreter's own flush must not fail again."""
    monkeypatch.setattr(sys, "stdout", _Gone())
    assert cli.run(["criteria"]) == cli.EXIT_OK
    assert sys.stdout is None


# ---- a file nested too deeply to parse is a finding, not a traceback

def test_check_reports_a_file_the_parser_cannot_take_instead_of_crashing():
    (finding,) = check_source(DEEP, "deep.py")
    assert finding.check == "PY-PARSE" and "too deeply" in finding.message


def test_check_and_finish_both_name_a_file_that_is_too_deep(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    (tmp_path / "deep.py").write_text(DEEP, encoding="utf-8")
    (tmp_path / "README.md").write_text("# demo\n", encoding="utf-8")
    assert cli.main(["check", str(tmp_path)]) == cli.EXIT_FINDINGS
    checked = capsys.readouterr()
    assert "PY-PARSE" in checked.out and "Traceback" not in checked.err
    assert cli.main(["finish", str(tmp_path), "--scope", "code"]) == cli.EXIT_OK
    assert "nested too deeply" in capsys.readouterr().err


# ---- a link to a directory is not followed

def test_a_link_to_a_directory_is_not_followed_by_check_and_the_readme_says_so(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    real = tmp_path / "real"
    real.mkdir()
    (real / "a.py").write_text("from os import *\n", encoding="utf-8")
    (tmp_path / "link").symlink_to("real", target_is_directory=True)
    (tmp_path / "README.md").write_text("# demo\n", encoding="utf-8")
    assert cli.main(["check", str(tmp_path)]) == cli.EXIT_FINDINGS
    out = capsys.readouterr().out
    assert "real/a.py" in out and "link/a.py" not in out
    readme = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
    assert "does not follow a symbolic link to a directory" in readme


def test_a_tree_whose_only_python_is_behind_a_directory_link_has_nothing_to_check(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "a.py").write_text("from os import *\n", encoding="utf-8")
    target = tmp_path / "target"
    target.mkdir()
    (target / "link").symlink_to("../elsewhere", target_is_directory=True)
    assert cli.main(["check", str(target)]) == cli.EXIT_CANNOT_RUN
    assert "nothing to report" in capsys.readouterr().err
