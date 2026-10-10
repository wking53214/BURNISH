"""The critic speaks about what was measured, quotes it, and counts nothing itself."""

from pathlib import Path

from warden.models import defects_from_ghost
from warden.roles import Facts
from warden.suite import SuiteRun

from burnish.critic import PoetryCritic


def _pkg(root: Path, readme: str) -> None:
    (root / "pkg").mkdir()
    (root / "pkg" / "__init__.py").write_text('"""owns nothing declared."""\n', encoding="utf-8")
    (root / "README.md").write_text(readme, encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.0.1"\ndescription = "demo"\n', encoding="utf-8")


def test_no_measurements_means_unknown_not_clean(tmp_path: Path):
    _pkg(tmp_path, "# demo\n")
    report = PoetryCritic().critique(tmp_path)
    assert any("UNKNOWN" in item for item in report.unknown)


def test_a_green_suite_is_quoted_from_the_facts(tmp_path: Path):
    _pkg(tmp_path, "# demo\n")
    facts = Facts(suite=SuiteRun(ran=True, passed=7), remaining=(), cycles=2)
    report = PoetryCritic().critique(tmp_path, facts=facts)
    assert any("7 passed" in item for item in report.what_is_beautiful)


def test_a_red_suite_is_not_good_enough(tmp_path: Path):
    _pkg(tmp_path, "# demo\n")
    facts = Facts(suite=SuiteRun(ran=True, passed=3, failed=1), remaining=(), cycles=0)
    report = PoetryCritic().critique(tmp_path, facts=facts)
    assert report.good_enough is False and "isn't good enough yet" in report.verdict


def test_what_ghost_still_reports_is_named_as_ugly(tmp_path: Path):
    _pkg(tmp_path, "# demo\n")
    remaining = defects_from_ghost([{"id": "ghost-9", "severity": "minor", "status": "confirmed",
                                     "summary": "a long function"}])
    report = PoetryCritic().critique(tmp_path, facts=Facts(suite=None, remaining=remaining, cycles=1))
    assert any("ghost-9" in item and "a long function" in item for item in report.what_is_ugly)
    assert any("not run" in item for item in report.what_is_unfinished)


def test_the_critic_checks_a_readme_test_count_against_the_measured_suite(tmp_path: Path):
    """Changed on purpose: it used to ignore test counts in the README. It now only reports them, never counts."""
    _pkg(tmp_path, "# demo\n\nAll 16 tests passed unmodified on python3.\n")
    unmeasured = PoetryCritic().critique(tmp_path)
    assert [c.note for c in unmeasured.claims] == [
        "The README says a count of 16; this is unmeasured because the test suite did not run."]
    assert unmeasured.good_enough
    wrong = PoetryCritic().critique(tmp_path, facts=Facts(suite=SuiteRun(ran=True, passed=5), remaining=(), cycles=1))
    assert not wrong.good_enough
    assert "The README says a count of 16; the measured suite has 5 passing. These disagree." in wrong.unsupported[0]
    right = PoetryCritic().critique(tmp_path, facts=Facts(suite=SuiteRun(ran=True, passed=16), remaining=(), cycles=1))
    assert right.good_enough and right.claims[0].supported
