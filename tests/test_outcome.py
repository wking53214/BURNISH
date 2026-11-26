"""The critic ends with one of three outcomes, each with its own exit code (0.4.0).

Before 0.4.0 the critic had two answers, "good enough" or not, so a claim it could not check and a claim the tree
contradicts both ended in exit 1, and a reader could not tell "wrong" from "not looked at". Now FAIL means the evidence
contradicts a claim or the tree breaks a rule, INCOMPLETE means nothing is contradicted but a claim could not be
checked, and PASS means neither.
"""

from pathlib import Path

import pytest

from burnish import cli
from burnish.critic import Outcome, PoetryCritic

PYPROJECT = ('[project]\nname = "demo"\nversion = "0.1.0"\n'
             'dependencies = ["cns @ git+https://github.com/example/CNS.git@v2.0.0"]\n')


def _tree(root: Path, readme: str, pyproject: str = PYPROJECT, source: str = '"""demo."""\n') -> Path:
    (root / "demo").mkdir()
    (root / "demo" / "__init__.py").write_text(source, encoding="utf-8")
    (root / "README.md").write_text(readme, encoding="utf-8")
    (root / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    return root


def _run(root: Path, capsys: pytest.CaptureFixture[str], *extra: str) -> tuple[int, str]:
    code = cli.main(["critic", str(root), *extra])
    return code, capsys.readouterr().out


def test_a_readme_with_nothing_to_doubt_passes_and_exits_0(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    _tree(tmp_path, "# demo\n\nA small demo.\n")
    report = PoetryCritic().critique(tmp_path)
    assert report.outcome is Outcome.PASS and report.good_enough
    code, out = _run(tmp_path, capsys)
    assert code == 0 and "Outcome: PASS" in out


def test_a_claim_nothing_measured_is_incomplete_and_exits_4(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    _tree(tmp_path, "# demo\n\n240 tests pass.\n")
    report = PoetryCritic().critique(tmp_path)
    assert report.outcome is Outcome.INCOMPLETE and not report.good_enough
    assert "This is not a pass" in report.verdict
    code, out = _run(tmp_path, capsys)
    assert code == 4 and "Outcome: INCOMPLETE" in out


def test_a_collected_count_that_matches_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    _tree(tmp_path, "# demo\n\n240 test cases are collected in this tree.\n")
    assert _run(tmp_path, capsys, "--collected", "240")[0] == 0


def test_a_claim_the_tree_contradicts_fails_and_exits_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    _tree(tmp_path, "# demo\n\nDemo is pinned to CNS v1.9.0.\n")
    report = PoetryCritic().critique(tmp_path)
    assert report.outcome is Outcome.FAIL and not report.good_enough
    code, out = _run(tmp_path, capsys)
    assert code == 1 and "Outcome: FAIL" in out


def test_a_count_that_cannot_be_true_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    _tree(tmp_path, "# demo\n\n240 test cases are collected in this tree.\n")
    assert _run(tmp_path, capsys, "--collected", "241")[0] == 1


def test_a_passing_count_below_the_collected_count_is_incomplete_not_a_fail(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """240 passing of 241 collected can be true (one may have failed or been skipped): not refuted, not confirmed."""
    _tree(tmp_path, "# demo\n\n240 tests pass.\n")
    assert _run(tmp_path, capsys, "--collected", "241")[0] == 4


def test_a_contradiction_beside_an_unchecked_claim_is_still_a_fail(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nDemo is pinned to CNS v1.9.0.\n\n240 tests pass.\n")
    report = PoetryCritic().critique(tmp_path)
    assert report.outcome is Outcome.FAIL
    assert len(report.unsupported) >= 2   # both are still listed; the outcome is the worst of them


def test_a_file_that_does_not_parse_is_a_fail_not_missing_evidence(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nA small demo.\n", source="def broken(:\n")
    assert PoetryCritic().critique(tmp_path).outcome is Outcome.FAIL


def test_a_broken_pyproject_behind_a_claim_is_incomplete(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nThere are no runtime dependencies.\n", pyproject='[project]\nname = "demo"\ndependencies = [\n')
    assert PoetryCritic().critique(tmp_path).outcome is Outcome.INCOMPLETE


def test_an_undeclared_import_inside_a_function_is_incomplete(tmp_path: Path):
    source = '"""demo."""\n\n\ndef get():\n    """Get."""\n    import requests\n    return requests\n'
    plain = '[project]\nname = "demo"\nversion = "0.1.0"\ndependencies = []\n'
    _tree(tmp_path, "# demo\n\nThere are no runtime dependencies.\n", pyproject=plain, source=source)
    assert PoetryCritic().critique(tmp_path).outcome is Outcome.INCOMPLETE


def test_an_earned_4_is_kept_when_the_report_cannot_be_delivered(tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                                                 monkeypatch: pytest.MonkeyPatch):
    _tree(tmp_path, "# demo\n\n240 tests pass.\n")
    monkeypatch.setattr("sys.stdout", None)
    assert cli.main(["critic", str(tmp_path)]) == 4
    capsys.readouterr()


def test_pin_and_dependency_claims_with_no_pyproject_end_incomplete(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """Item 47 of the remediation plan: with nothing to check the claims against, the run cannot end PASS."""
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text('"""demo."""\n', encoding="utf-8")
    (tmp_path / "README.md").write_text("# demo\n\nIt does not do much. Pinned to Warden v0.11.0.\n", encoding="utf-8")
    report = PoetryCritic().critique(tmp_path)
    assert report.outcome.value == "INCOMPLETE"
    (row,) = [c for c in report.claims if c.kind == "pin"]
    assert row.agreement == "unchecked" and row.provenance is not None
    assert row.provenance.evidence[0].path == "pyproject.toml" and "There is no pyproject.toml" in row.provenance.reason
    assert cli.main(["critic", str(tmp_path)]) == cli.EXIT_INCOMPLETE
    capsys.readouterr()
