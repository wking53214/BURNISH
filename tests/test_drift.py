"""READMEs that say something the tree contradicts: a pin, a dependency list, a test count."""

from pathlib import Path

import pytest

from burnish import cli
from burnish.critic import PoetryCritic
from burnish.drift import check_test_claims, check_tree_claims

SHA = "ec551d8e10f82b6e3e681593a97011ae517d360b"
PYPROJECT = f"""[project]
name = "demo"
version = "0.1.0"
description = "demo"
dependencies = [
    "warden @ git+https://github.com/example/Warden.git@{SHA}",  # Warden 0.13.1, not tagged
    "cns @ git+https://github.com/example/CNS.git@5252ceebe98185f7be81212d988055ccf9884568",  # v1.8.0
]
"""
IMPORTS_BOTH = '"""demo."""\n\nimport json\n\nimport cns\nimport warden\n\nfrom . import sibling\n'


def _tree(root: Path, readme: str, pyproject: str = PYPROJECT, source: str = IMPORTS_BOTH) -> Path:
    (root / "demo").mkdir()
    (root / "demo" / "__init__.py").write_text(source, encoding="utf-8")
    (root / "demo" / "sibling.py").write_text('"""s."""\n', encoding="utf-8")
    (root / "README.md").write_text(readme, encoding="utf-8")
    (root / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    return root


def _kinds(root: Path) -> list[str]:
    return [d.kind for d in check_tree_claims(root)]


# ---- pins

@pytest.mark.parametrize("sentence", [
    "Demo is pinned to Warden v0.11.0.",
    "This installs Warden at its pinned tag `v0.11.0`, which Demo plugs into.",
    "Demo is pinned to Warden `v0.11.0` (see below).",
    "Warden is pinned to tag 0.11.5.",
])
def test_a_pin_claim_that_pyproject_does_not_have_is_reported(tmp_path: Path, sentence: str):
    _tree(tmp_path, f"# demo\n\n{sentence}\n")
    drifts = check_tree_claims(tmp_path)
    assert [d.kind for d in drifts] == ["pin"]
    assert "pyproject.toml pins warden at commit ec551d8" in drifts[0].problem and "not tagged" not in drifts[0].claim


def test_a_pin_claim_that_pyproject_confirms_is_not_reported(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nDemo is pinned to Warden 0.13.1, and to CNS `v1.8.0`.\n")
    assert check_tree_claims(tmp_path) == []


def test_a_pin_claim_is_judged_against_the_dependency_it_names(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nDemo is pinned to CNS v0.13.1.\n")
    assert _kinds(tmp_path) == ["pin"]   # 0.13.1 is Warden's release, not CNS's


def test_a_commit_claim_must_be_the_commit_in_pyproject(tmp_path: Path):
    _tree(tmp_path, f"# demo\n\nDemo is pinned to Warden commit {SHA[:7]}.\n")
    assert check_tree_claims(tmp_path) == []
    other = tmp_path / "other"
    other.mkdir()
    _tree(other, "# demo\n\nDemo is pinned to Warden commit 1234abc.\n")
    assert _kinds(other) == ["pin"]


def test_pointing_at_pyproject_instead_of_restating_is_clean(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nDemo is pinned to one exact Warden commit, recorded in `pyproject.toml`.\n")
    assert check_tree_claims(tmp_path) == []


def test_a_pin_inside_a_code_block_is_an_example_not_a_claim(tmp_path: Path):
    _tree(tmp_path, "# demo\n\n```text\nDemo is pinned to Warden v0.11.0.\n```\n")
    assert check_tree_claims(tmp_path) == []


def test_a_pin_claim_with_no_git_dependency_at_all_is_reported(tmp_path: Path):
    bare = '[project]\nname = "demo"\nversion = "0.1.0"\ndependencies = ["requests>=2"]\n'
    _tree(tmp_path, "# demo\n\nDemo is pinned to Warden v0.11.0.\n", pyproject=bare)
    drifts = check_tree_claims(tmp_path)
    assert [d.kind for d in drifts] == ["pin"] and "pins no git dependency" in drifts[0].problem


# ---- dependencies

def test_no_other_dependencies_is_reported_when_the_code_imports_and_declares_a_second(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nThis installs Warden, which Demo plugs into. No other dependencies.\n")
    drifts = check_tree_claims(tmp_path)
    assert [d.kind for d in drifts] == ["dependencies"]
    assert "cns (declared in pyproject.toml, imported in 1 file(s))" in drifts[0].problem
    assert "warden" not in drifts[0].problem.replace("beyond the ones it names", "")


def test_no_dependencies_names_every_declared_one(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nIt has no dependencies.\n")
    problem = check_tree_claims(tmp_path)[0].problem
    assert "cns" in problem and "warden" in problem


def test_naming_every_dependency_makes_the_claim_true(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nIt needs Warden and CNS. No other dependencies.\n")
    assert check_tree_claims(tmp_path) == []


def test_an_import_that_is_not_declared_is_reported(tmp_path: Path):
    plain = '[project]\nname = "demo"\nversion = "0.1.0"\ndependencies = []\n'
    _tree(tmp_path, "# demo\n\nStandard library only.\n", pyproject=plain, source='"""d."""\n\nimport json\nimport requests\n')
    problem = check_tree_claims(tmp_path)[0].problem
    assert "requests (imported in 1 file(s), not declared)" in problem


def test_a_true_no_dependencies_claim_is_clean(tmp_path: Path):
    plain = '[project]\nname = "demo"\nversion = "0.1.0"\ndependencies = []\n'
    _tree(tmp_path, "# demo\n\nThere are no dependencies.\n", pyproject=plain, source='"""d."""\n\nimport json\n')
    assert check_tree_claims(tmp_path) == []


def test_a_quoted_example_of_the_phrase_is_not_a_claim(tmp_path: Path):
    _tree(tmp_path, '# demo\n\nA sentence such as "No other dependencies" is checked against the tree.\n')
    assert check_tree_claims(tmp_path) == []


def test_a_tree_without_pyproject_has_nothing_to_contradict(tmp_path: Path):
    (tmp_path / "README.md").write_text("# demo\n\nPinned to Warden v0.11.0. No other dependencies.\n", encoding="utf-8")
    assert check_tree_claims(tmp_path) == []


# ---- test counts

@pytest.mark.parametrize("sentence", ["240 test cases are collected in this tree.", "The suite has 240 tests.",
                                      "There are 240 tests in total."])
def test_a_test_count_with_nothing_measured_is_unverifiable(sentence: str):
    drifts = check_test_claims(f"# demo\n\n{sentence}\n")
    assert [(d.kind, d.verdict) for d in drifts] == [("tests", "unverifiable")]
    assert "counts no tests" in drifts[0].problem


def test_a_test_count_that_matches_the_collected_count_is_clean():
    assert check_test_claims("The suite has 247 tests.\n", collected=247) == []


def test_a_test_count_that_differs_from_the_collected_count_is_reported():
    drifts = check_test_claims("240 test cases are collected in this tree.\n", collected=247)
    assert [(d.kind, d.verdict) for d in drifts] == [("tests", "disagrees")]
    assert "collects 247" in drifts[0].problem


def test_a_lower_bound_is_checked_against_the_collected_count():
    assert check_test_claims("At least 200 tests exist.\n", collected=247) == []
    assert len(check_test_claims("At least 300 tests exist.\n", collected=247)) == 1


def test_a_passing_claim_is_refuted_only_when_it_cannot_be_true():
    assert check_test_claims("247 tests pass.\n", collected=247) == []
    assert check_test_claims("200 tests pass.\n", collected=247) == []   # skips and failures can explain fewer
    assert len(check_test_claims("250 tests pass.\n", collected=247)) == 1


def test_a_history_or_a_file_count_is_not_a_claim_about_the_suite():
    assert check_test_claims("Added 5 tests. test_x.py has 3 tests.\n") == []


# ---- the critics

def test_the_critic_reports_all_three_classes_in_one_fixture_readme(tmp_path: Path):
    _tree(tmp_path, "# demo\n\nDemo is pinned to Warden v0.11.0 and plugs into it. No other dependencies.\n\n"
                    "240 test cases are collected in this tree.\n")
    report = PoetryCritic().critique(tmp_path)
    assert not report.good_enough
    text = " ".join(report.unsupported)
    assert "pyproject.toml pins warden" in text and "cns (declared" in text and "counts no tests" in text


def test_the_critic_judges_a_test_count_against_a_collected_count(tmp_path: Path):
    _tree(tmp_path, "# demo\n\n240 test cases are collected in this tree.\n")
    assert PoetryCritic().critique(tmp_path, collected=240).good_enough
    wrong = PoetryCritic().critique(tmp_path, collected=247)
    assert not wrong.good_enough and "collects 247" in wrong.unsupported[0]


def test_a_measured_suite_judges_the_count_not_the_collected_rule(tmp_path: Path):
    from cns.seat import Facts
    from cns.suite import SuiteRun

    _tree(tmp_path, "# demo\n\n240 test cases are collected in this tree.\n")
    facts = Facts(suite=SuiteRun(ran=True, passed=240), remaining=(), cycles=1)
    assert PoetryCritic().critique(tmp_path, facts=facts).good_enough


def test_the_critic_cli_exits_1_on_a_contradicted_readme(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    _tree(tmp_path, "# demo\n\nDemo is pinned to Warden v0.11.0.\n")
    assert cli.main(["critic", str(tmp_path)]) == 1
    assert "pyproject.toml pins warden" in capsys.readouterr().out


def test_the_critic_cli_takes_the_collected_count(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    _tree(tmp_path, "# demo\n\n240 test cases are collected in this tree.\n")
    assert cli.main(["critic", str(tmp_path), "--collected", "240"]) == 0
    assert cli.main(["critic", str(tmp_path), "--collected", "241"]) == 1
    assert cli.main(["critic", str(tmp_path)]) == 1
    capsys.readouterr()


def test_collected_must_be_a_whole_number(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    _tree(tmp_path, "# demo\n")
    with pytest.raises(SystemExit) as stopped:
        cli.main(["critic", str(tmp_path), "--collected", "many"])
    assert stopped.value.code == 2
    capsys.readouterr()


def test_the_readme_critic_cli_catches_each_class_at_the_minimum_tier(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    readme = ("# Demo\n\nDemo checks things for you.\n\n## Install\n\n```bash\npip install demo\n```\n\n"
              "## Usage\n\n```bash\ndemo run\n```\n\n## What it does not do\n\nIt does not fix anything.\n\n"
              "## Contributing\n\nPull requests welcome.\n\n## License\n\nMIT.\n\n")
    plain = tmp_path / "plain"
    plain.mkdir()
    _tree(plain, readme)
    assert cli.main(["readme-critic", str(plain)]) == 0
    capsys.readouterr()
    for index, sentence in enumerate(["Pinned to Warden v0.11.0.", "No other dependencies beyond Warden.",
                                      "240 test cases are collected in this tree."]):
        root = tmp_path / f"case{index}"
        root.mkdir()
        _tree(root, readme + sentence + "\n")
        assert cli.main(["readme-critic", str(root)]) == 1, sentence
        assert "Claims the tree contradicts or cannot back" in capsys.readouterr().out
    ok = tmp_path / "ok"
    ok.mkdir()
    _tree(ok, readme + "240 test cases are collected in this tree.\n")
    assert cli.main(["readme-critic", str(ok), "--collected", "240"]) == 0
    capsys.readouterr()
