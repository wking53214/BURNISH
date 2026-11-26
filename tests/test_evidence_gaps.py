"""Two places where Burnish read less than it said, found by checking an outside remediation plan against the code (2026-11-25).

`check` walked the tree with its own, shorter list of skipped folders, so it judged vendored, generated and fixture code
that every other command leaves out, and it read `.py` links the others skip. A `pyproject.toml` that is there but is not
valid TOML was treated as if there were none: the critic checked no pin and no dependency claim and said nothing, and
`inspect` printed a name and version read line by line as if the file had parsed.
"""

import json
from pathlib import Path

import pytest

from burnish import cli
from burnish.checks import check_tree, checkable_files
from burnish.critic import PoetryCritic
from burnish.drift import check_tree_claims
from burnish.files import pyproject_problem, python_files
from burnish.narrative import inspect_tree

#: A module every check would speak about: no docstring, a bare except, a comparison with None.
UGLY = "def f(x):\n    try:\n        return x == None\n    except:\n        pass\n"
BROKEN_TOML = '[project]\nname = "demo"\nversion = "1.0"\ndependencies = [\n'
VALID_TOML = '[project]\nname = "demo"\nversion = "1.0"\ndependencies = []\n'


def _tree(root: Path, readme: str, pyproject: str) -> Path:
    (root / "demo").mkdir()
    (root / "demo" / "__init__.py").write_text('"""demo."""\n', encoding="utf-8")
    (root / "README.md").write_text(readme, encoding="utf-8")
    (root / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    return root


# ---- one walk for every command

@pytest.mark.parametrize("folder", ["vendor", "third_party", "fixtures", "specimens", "env", ".tox", "demo.egg-info"])
def test_check_skips_the_folders_every_other_command_skips(tmp_path: Path, folder: str):
    (tmp_path / "own.py").write_text('"""own."""\n', encoding="utf-8")
    (tmp_path / folder).mkdir()
    (tmp_path / folder / "theirs.py").write_text(UGLY, encoding="utf-8")
    assert check_tree(tmp_path) == []


def test_check_and_the_critic_read_the_same_files(tmp_path: Path):
    for relative in ("a.py", "pkg/b.py", "vendor/c.py", "fixtures/d.py", "build/e.py", "tests/test_f.py"):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('"""x."""\n', encoding="utf-8")
    assert list(checkable_files(tmp_path)) == list(python_files(tmp_path))


def test_check_does_not_read_a_python_file_through_a_link(tmp_path: Path):
    outside = tmp_path / "outside.py"
    outside.write_text(UGLY, encoding="utf-8")
    target = tmp_path / "tree"
    target.mkdir()
    (target / "own.py").write_text('"""own."""\n', encoding="utf-8")
    (target / "linked.py").symlink_to(outside)
    assert check_tree(target) == []


def test_check_still_names_a_dangling_python_link_instead_of_skipping_it(tmp_path: Path):
    (tmp_path / "own.py").write_text('"""own."""\n', encoding="utf-8")
    (tmp_path / "gone.py").symlink_to(tmp_path / "nowhere.py")
    with pytest.raises(OSError, match="broken symbolic link"):
        check_tree(tmp_path)
    assert cli.main(["check", str(tmp_path)]) == 2


# ---- a broken pyproject.toml is said to be broken

def test_a_broken_pyproject_is_named_and_a_valid_or_missing_one_is_not(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(BROKEN_TOML, encoding="utf-8")
    assert "not valid TOML" in (pyproject_problem(tmp_path) or "")
    (tmp_path / "pyproject.toml").write_text(VALID_TOML, encoding="utf-8")
    assert pyproject_problem(tmp_path) is None
    (tmp_path / "pyproject.toml").unlink()
    assert pyproject_problem(tmp_path) is None


def test_a_pyproject_that_is_not_utf8_is_named(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_bytes(b'[project]\nname = "d\xffmo"\n')
    assert pyproject_problem(tmp_path) == "pyproject.toml is not valid UTF-8"


def test_a_dependency_claim_against_a_broken_pyproject_is_unchecked_not_silently_held(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nThere are no runtime dependencies.\n", BROKEN_TOML)
    (drift,) = check_tree_claims(tmp_path)
    assert drift.kind == "dependencies" and drift.verdict == "unchecked"
    assert "not valid TOML" in drift.problem and "not checked" in drift.problem


def test_a_pin_claim_against_a_broken_pyproject_is_unchecked(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nDemo is pinned to CNS v2.0.0.\n", BROKEN_TOML)
    (drift,) = check_tree_claims(tmp_path)
    assert drift.kind == "pin" and drift.verdict == "unchecked"


def test_the_critic_does_not_call_a_tree_good_enough_when_it_could_not_read_the_claims_evidence(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nThere are no runtime dependencies.\n", BROKEN_TOML)
    report = PoetryCritic().critique(tmp_path)
    assert not report.good_enough
    assert any("not valid TOML" in item and "not checked" in item for item in report.unsupported)
    assert any("not valid TOML" in item and "read line by line" in item for item in report.unknown)
    (row,) = [c for c in report.claims if c.label == "README claim (dependencies)"]
    assert row.agreement == "unchecked" and not row.supported


def test_a_broken_pyproject_with_no_claims_is_still_listed_as_unknown(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nA small demo.\n", BROKEN_TOML)
    assert check_tree_claims(tmp_path) == []
    assert any("not valid TOML" in item for item in PoetryCritic().critique(tmp_path).unknown)


def test_inspect_says_the_metadata_came_from_a_broken_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    _tree(tmp_path, "# demo\n", BROKEN_TOML)
    assert cli.main(["inspect", str(tmp_path)]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["name"] == "demo" and "not valid TOML" in shown["metadata_problem"]
    assert inspect_tree(tmp_path).metadata_problem == shown["metadata_problem"]


def test_inspect_reports_no_metadata_problem_for_a_valid_pyproject(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    _tree(tmp_path, "# demo\n", VALID_TOML)
    assert cli.main(["inspect", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["metadata_problem"] is None


def test_the_compiled_readme_says_the_version_may_be_wrong(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    _tree(tmp_path, "# demo\n", BROKEN_TOML)
    (tmp_path / "README.md").unlink()
    assert cli.main(["readme", str(tmp_path)]) == 0
    shown = " ".join(capsys.readouterr().out.split())
    assert "not valid TOML" in shown and "read line by line and may be wrong" in shown
