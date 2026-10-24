"""A command that could not look at anything must say so and exit 2; it must never report a clean result."""

from pathlib import Path

import pytest

from burnish import cli

PATH_COMMANDS = ["check", "critic", "readme-critic", "inspect", "readme", "finish", "cns"]
GOOD_PYTHON = '"""A module."""\n\n\ndef add(a: int, b: int) -> int:\n    """Add."""\n    return a + b\n'


def _run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _unreadable(monkeypatch: pytest.MonkeyPatch, filename: str) -> None:
    """Make reading one file fail the way a permission error does (chmod does nothing to a process running as root)."""
    real_text, real_bytes = Path.read_text, Path.read_bytes

    def refuse(self: Path) -> None:
        raise PermissionError(13, "Permission denied", str(self))

    def read_text(self: Path, *args: object, **kwargs: object) -> str:
        if self.name == filename:
            refuse(self)
        return real_text(self, *args, **kwargs)  # type: ignore[arg-type]  # forwarded unchanged

    def read_bytes(self: Path) -> bytes:
        if self.name == filename:
            refuse(self)
        return real_bytes(self)

    monkeypatch.setattr(Path, "read_text", read_text)
    monkeypatch.setattr(Path, "read_bytes", read_bytes)


@pytest.mark.parametrize("command", PATH_COMMANDS)
def test_a_path_that_does_not_exist_exits_2_and_says_so(command: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    code, out, err = _run(capsys, command, str(tmp_path / "missing"))
    assert code == 2
    assert "no such file or directory" in err and f"burnish {command}" in err
    assert "finding(s)" not in out + err and out == ""


@pytest.mark.parametrize("command", PATH_COMMANDS)
def test_a_directory_with_zero_files_exits_2(command: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    code, out, err = _run(capsys, command, str(tmp_path))
    assert code == 2 and "nothing to report" in err
    assert "0 finding" not in out + err and out == ""


@pytest.mark.parametrize("command", PATH_COMMANDS)
def test_a_path_that_is_a_file_exits_2(command: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    (tmp_path / "one.py").write_text(GOOD_PYTHON, encoding="utf-8")
    code, _, err = _run(capsys, command, str(tmp_path / "one.py"))
    assert code == 2 and "not a directory" in err


@pytest.mark.parametrize("command", ["check", "critic", "inspect", "readme", "finish", "cns"])
def test_a_tree_whose_only_python_is_in_a_skipped_folder_has_nothing_to_read(command: str, tmp_path: Path,
                                                                            capsys: pytest.CaptureFixture[str]):
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "x.py").write_text(GOOD_PYTHON, encoding="utf-8")
    (tmp_path / "notes.txt").write_text("not python\n", encoding="utf-8")
    code, out, err = _run(capsys, command, str(tmp_path))
    assert code == 2 and out == ""


def test_check_with_only_a_readme_has_no_python_to_check(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    (tmp_path / "README.md").write_text("# demo\n", encoding="utf-8")
    code, _, err = _run(capsys, "check", str(tmp_path))
    assert code == 2 and "Python files" in err


def test_readme_critic_with_only_python_has_no_readme_to_read(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    (tmp_path / "one.py").write_text(GOOD_PYTHON, encoding="utf-8")
    code, out, err = _run(capsys, "readme-critic", str(tmp_path))
    assert code == 2 and "README" in err and out == ""


def test_inspect_accepts_a_readme_with_no_python_and_critic_refuses_it(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    (tmp_path / "README.md").write_text("# demo\n", encoding="utf-8")
    assert _run(capsys, "inspect", str(tmp_path))[0] == 0
    assert _run(capsys, "critic", str(tmp_path))[0] == 2


@pytest.mark.parametrize("readme", [b"# hi\n", b"# hi\n\xff\xfe\x00 not utf-8\n", b"# demo\n\nA powerful, seamless tool.\n"],
                         ids=["trivial", "not-utf-8", "marketing"])
def test_critic_on_a_readme_with_no_code_says_there_is_nothing_to_check(readme: bytes, tmp_path: Path,
                                                                        capsys: pytest.CaptureFixture[str]):
    """The verdict "the story is consistent" over a tree with no code would compare the README with nothing."""
    (tmp_path / "README.md").write_bytes(readme)
    code, out, err = _run(capsys, "critic", str(tmp_path))
    assert code == 2 and out == ""
    assert "nothing to check" in err and "consistent" not in err and "Traceback" not in err


def test_critic_with_a_readme_and_a_manifest_but_no_python_still_has_nothing_to_check(tmp_path: Path,
                                                                                      capsys: pytest.CaptureFixture[str]):
    (tmp_path / "README.md").write_text("# demo\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\nversion = "0.1.0"\n', encoding="utf-8")
    assert _run(capsys, "critic", str(tmp_path))[0] == 2


@pytest.mark.parametrize("command", ["readme-critic", "inspect", "readme", "cns", "finish"])
def test_the_other_commands_still_read_a_readme_with_no_python(command: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    (tmp_path / "README.md").write_text("# hi\n", encoding="utf-8")
    assert _run(capsys, command, str(tmp_path))[0] in (0, 1)


def test_critic_still_reads_a_trivial_readme_beside_code(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    (tmp_path / "README.md").write_text("# hi\n", encoding="utf-8")
    (tmp_path / "one.py").write_text(GOOD_PYTHON, encoding="utf-8")
    code, out, _ = _run(capsys, "critic", str(tmp_path))
    assert code in (0, 1) and out.startswith("# Claims critic")


@pytest.mark.parametrize("command", ["critic", "readme", "inspect", "cns", "finish"])
def test_python_with_no_readme_is_reported_not_refused(command: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """The README's exit-code section says so: a missing README is a finding or a generated file, and the exit is 0."""
    (tmp_path / "one.py").write_text(GOOD_PYTHON, encoding="utf-8")
    code, out, err = _run(capsys, command, str(tmp_path))
    assert code == 0 and out != ""
    said = {"critic": "There is no README", "inspect": '"readme_exists": false', "readme": "# ", "finish": "README.md"}
    if command in said:
        assert said[command] in out


def test_an_unreadable_python_file_makes_check_exit_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                      capsys: pytest.CaptureFixture[str]):
    (tmp_path / "locked.py").write_text(GOOD_PYTHON, encoding="utf-8")
    _unreadable(monkeypatch, "locked.py")
    code, out, err = _run(capsys, "check", str(tmp_path))
    assert code == 2 and "cannot read" in err and "locked.py" in err
    assert "0 finding" not in out + err


@pytest.mark.parametrize("name", [".py", "gone.py"])
def test_a_broken_symlink_makes_check_exit_2_and_names_the_true_reason(name: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    (tmp_path / "ok.py").write_text(GOOD_PYTHON, encoding="utf-8")
    (tmp_path / name).symlink_to(tmp_path / "no-such-target")
    code, out, err = _run(capsys, "check", str(tmp_path))
    assert code == 2 and out == ""
    assert "broken symbolic link" in err and name in err
    assert "Is a directory" not in err and "0 finding" not in err


@pytest.mark.parametrize("name", [".py", "gone.py", "sub/deep.py"])
@pytest.mark.parametrize("command", ["check", "critic", "inspect", "readme", "cns", "finish"])
def test_a_broken_py_symlink_among_real_files_makes_every_command_exit_2(command: str, name: str, tmp_path: Path,
                                                                        capsys: pytest.CaptureFixture[str]):
    """A dangling link is an unreadable file, not an absent one: the commands that skip links must say so, as check does."""
    (tmp_path / "ok.py").write_text(GOOD_PYTHON, encoding="utf-8")
    (tmp_path / "README.md").write_text("# demo\n\nA thing.\n", encoding="utf-8")
    (tmp_path / name).parent.mkdir(exist_ok=True)
    (tmp_path / name).symlink_to(tmp_path / "no-such-target")
    code, out, err = _run(capsys, command, str(tmp_path))
    assert code == 2 and out == ""
    assert "broken symbolic link" in err and Path(name).name in err
    assert "0 finding" not in err


def test_a_broken_py_symlink_does_not_stop_readme_critic_which_reads_no_python(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    (tmp_path / "README.md").write_text("# demo\n\nA thing.\n", encoding="utf-8")
    (tmp_path / "gone.py").symlink_to(tmp_path / "no-such-target")
    assert _run(capsys, "readme-critic", str(tmp_path))[0] in (0, 1)


@pytest.mark.parametrize("name", ["README.md", "readme", "README.rst", "Readme.txt"])
@pytest.mark.parametrize("with_python", [False, True])
@pytest.mark.parametrize("command", ["critic", "inspect", "readme", "cns", "finish", "readme-critic"])
def test_a_broken_readme_symlink_makes_every_command_that_reads_or_writes_the_readme_exit_2(
        command: str, with_python: bool, name: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """Not "no README": `finish` would otherwise propose creating README.md, and a write through the link creates its target."""
    outside = tmp_path / "outside"
    outside.mkdir()
    target = tmp_path / "repo"
    target.mkdir()
    if with_python:
        (target / "ok.py").write_text(GOOD_PYTHON, encoding="utf-8")
    (target / name).symlink_to(outside / "created-by-a-write.md")
    code, out, err = _run(capsys, command, str(target))
    assert code == 2 and out == ""
    assert "broken symbolic link" in err and name in err
    assert "found no" not in err
    assert list(outside.iterdir()) == []


def test_check_does_not_read_the_readme_so_a_broken_readme_link_does_not_stop_it(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    (tmp_path / "ok.py").write_text(GOOD_PYTHON, encoding="utf-8")
    (tmp_path / "README.md").symlink_to(tmp_path / "no-such-target")
    assert _run(capsys, "check", str(tmp_path))[0] == 0


@pytest.mark.parametrize("with_python", [False, True])
def test_a_broken_readme_symlink_is_named_as_one_by_readme_critic(with_python: bool, tmp_path: Path,
                                                                  capsys: pytest.CaptureFixture[str]):
    """It used to say it "found no README to read", which is not the reason."""
    if with_python:
        (tmp_path / "ok.py").write_text(GOOD_PYTHON, encoding="utf-8")
    (tmp_path / "README.md").symlink_to(tmp_path / "no-such-target")
    code, out, err = _run(capsys, "readme-critic", str(tmp_path))
    assert code == 2 and out == ""
    assert "broken symbolic link" in err and "README.md" in err
    assert "found no README" not in err


@pytest.mark.parametrize("command", ["critic", "readme-critic", "inspect", "readme", "finish"])
def test_an_unreadable_readme_makes_the_command_exit_2(command: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                       capsys: pytest.CaptureFixture[str]):
    (tmp_path / "README.md").write_text("# demo\n\nA thing.\n", encoding="utf-8")
    (tmp_path / "one.py").write_text(GOOD_PYTHON, encoding="utf-8")
    _unreadable(monkeypatch, "README.md")
    code, out, err = _run(capsys, command, str(tmp_path))
    assert code == 2 and "cannot read" in err and "README.md" in err and out == ""


def test_a_clean_tree_still_exits_0_and_a_dirty_one_still_exits_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    (tmp_path / "ok.py").write_text(GOOD_PYTHON, encoding="utf-8")
    assert _run(capsys, "check", str(tmp_path))[0] == 0
    (tmp_path / "bad.py").write_text('"""Bad."""\n\n\ndef f() -> None:\n    """F."""\n    try:\n        pass\n    except:\n        pass\n',
                                     encoding="utf-8")
    code, out, _ = _run(capsys, "check", str(tmp_path))
    assert code == 1 and "PY-EXC" in out


def test_a_usage_error_exits_2(capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit) as stopped:
        cli.main(["check", "--no-such-flag"])
    assert stopped.value.code == 2
    capsys.readouterr()


def test_informational_commands_need_no_path(capsys: pytest.CaptureFixture[str]):
    assert _run(capsys, "criteria")[0] == 0
    assert _run(capsys, "languages")[0] == 0
