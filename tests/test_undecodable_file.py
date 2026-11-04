"""A Python file that is not valid UTF-8 is a finding for `burnish check`, not a clean file.

`checks.py` read files with `errors="replace"`, so a file holding a literal 0xff byte (which Python cannot compile) was
repaired in memory, parsed, and reported as "0 finding(s)" with exit 0, while `burnish finish` on the same file said
"not valid UTF-8". The file is now read strictly: an undecodable file is a `PY-PARSE` finding that says so, and `check`
exits as it does for any finding. `finish` is unchanged.
"""

from burnish import cli
from burnish.checks import check_tree


def _tree(tmp_path):
    (tmp_path / "ok.py").write_text('"""A clean module."""\n', encoding="utf-8")
    (tmp_path / "bad.py").write_bytes(b'"""A module with a stray byte."""\n# a stray byte: \xff\n')
    return tmp_path


def test_an_undecodable_python_file_is_a_finding_that_says_why(tmp_path):
    findings = check_tree(_tree(tmp_path))
    assert [f.path for f in findings] == ["bad.py"]
    (found,) = findings
    assert found.check == "PY-PARSE" and "not valid UTF-8" in found.message and "0xff" in found.message


def test_the_command_reports_it_and_exits_as_for_any_finding(tmp_path, capsys):
    code = cli.main(["check", str(_tree(tmp_path))])
    out, err = capsys.readouterr()
    assert code == cli.EXIT_FINDINGS
    assert "bad.py:" in out and "not valid UTF-8" in out
    assert "1 finding(s)" in err and "0 finding(s)" not in err


def test_a_tree_of_valid_files_is_unchanged(tmp_path, capsys):
    (tmp_path / "ok.py").write_text('"""A clean module."""\n', encoding="utf-8")
    assert cli.main(["check", str(tmp_path)]) == cli.EXIT_OK
    assert "0 finding(s)" in capsys.readouterr().err


def test_finish_still_says_not_valid_utf8_for_the_same_file(tmp_path, capsys):
    _tree(tmp_path)
    cli.main(["finish", str(tmp_path)])
    out, err = capsys.readouterr()
    assert "not valid UTF-8" in out + err
