"""The README keeps its honest sections, names only things that exist, and its numbers and ledger match the tree.

A claim of "works" in the README names a test, a CI job or a command. This file fails if a named test is gone, if the
ledger cites a version or date the CHANGELOG does not have, if a marketing word comes back, or if a number the README
states stops being true.
"""

import re
import tomllib
from pathlib import Path

from burnish.checks import CHECK_IDS
from burnish.drift import check_test_claims
from burnish.readme_critic import Tier

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
CHANGELOG = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

REQUIRED_HEADINGS = (
    "## What this is",
    "## Install",
    "## Usage",
    "## What works, and what shows it",
    "## What does not work, or is not proven",
    "## Known defects (open)",
    "## What broke and how it was fixed",
    "## Self-hosting",
    "## Ceilings code cannot fix",
)
BANNED_WORDS = ("robust", "powerful", "production-ready", "production ready", "seamless", "comprehensive",
                "blazing", "enterprise", "battle-tested", "state-of-the-art")
LEDGER_HEADING = "## What broke and how it was fixed"


def section(title_start: str) -> str:
    start = README.index(title_start)
    following = re.search(r"^## ", README[start + 1:], re.M)
    return README[start:start + 1 + following.start()] if following else README[start:]


def test_the_readme_keeps_the_sections_it_promises_in_order():
    positions = [README.index(heading) for heading in REQUIRED_HEADINGS]
    assert positions == sorted(positions)
    assert all(README.count(heading + "\n") == 1 for heading in REQUIRED_HEADINGS)


def test_every_test_the_readme_names_exists():
    named = set(re.findall(r"`(tests/test_\w+\.py)(?:::(\w+))?`", README))
    assert named, "the README names no tests"
    for path, function in named:
        source = (ROOT / path).read_text(encoding="utf-8")
        if function:
            assert re.search(rf"^\s*def {function}\(", source, re.M), f"{path}::{function} is named in the README"


def test_tests_named_by_function_alone_in_the_ledger_exist():
    everything = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "tests").glob("test_*.py"))
    for function in re.findall(r"`(test_\w+)`", section(LEDGER_HEADING)):
        assert re.search(rf"^\s*def {function}\(", everything, re.M), function


def test_every_version_and_date_in_the_ledger_is_a_changelog_heading():
    ledger = section(LEDGER_HEADING)
    released = dict(re.findall(r"^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})$", CHANGELOG, re.M))
    cited = re.findall(r"^\*\*(\d+\.\d+\.\d+)\*\* \((\d{4}-\d{2}-\d{2})", ledger, re.M)
    assert cited, "the ledger cites no version"
    for version, date in cited:
        assert released.get(version) == date, f"{version} is dated {released.get(version)} in the CHANGELOG, not {date}"
    mentioned = set(re.findall(r"\b0\.\d+\.\d+\b", ledger))
    assert mentioned <= set(released), mentioned - set(released)


def test_every_ci_job_the_readme_names_is_in_the_workflow():
    named = set(re.findall(r"`(python|rust|cpp23)`", README))
    assert named == {"python", "rust", "cpp23"}
    for job in named:
        assert re.search(rf"^  {job}:", WORKFLOW, re.M), job


def test_the_readme_uses_no_marketing_words():
    lowered = README.lower()
    assert [word for word in BANNED_WORDS if word in lowered] == []


def test_the_readme_has_no_em_or_en_dash():
    assert "—" not in README and "–" not in README


def test_the_eight_python_checks_the_readme_names_are_the_checks_the_code_has():
    assert len(CHECK_IDS) == 8, "the README says eight Python checks"
    readme_ids = set(re.findall(r"`(PY-[A-Z]+)`", README))
    assert readme_ids == set(CHECK_IDS)
    assert "eight" in README.lower()


def test_the_three_readme_tiers_the_readme_names_are_the_tiers_the_code_has():
    assert len(Tier) == 3
    assert "Three tiers" in README


def test_the_rust_release_the_readme_names_is_the_toolchain_file_release():
    toolchain = tomllib.loads((ROOT / "exemplars" / "rust" / "rust-toolchain.toml").read_text(encoding="utf-8"))
    assert f'channel = "{toolchain["toolchain"]["channel"]}"' in README


def test_the_readme_names_the_cns_pin_the_dependency_line_has():
    cns = next(dep for dep in PYPROJECT["project"]["dependencies"] if dep.startswith("cns @"))
    assert cns.endswith("@v2.0.0")
    assert "from `v1.9.0` to `v2.0.0`" in README and "(`@v2.0.0`)" in README
    assert "b13e5d2f9e0e4291725f82794b89117c3d840ac1" in (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_the_stack_doc_does_not_call_the_public_cns_repository_private():
    stack = (ROOT / "STACK.md").read_text(encoding="utf-8")
    assert "CNS](https://github.com/wking53214/CNS) (public)" in stack
    assert not re.search(r"CNS[^.\n]*\bprivate\b", stack, re.I)


def test_no_test_is_expected_to_fail_and_skip_markers_are_only_the_conditional_ones_the_readme_names():
    for path in (ROOT / "tests").glob("test_*.py"):
        if path.name == Path(__file__).name:
            continue
        source = path.read_text(encoding="utf-8")
        assert not re.search(r"pytest\.mark\.xfail|pytest\.xfail\(|xfail_strict", source), path.name
        assert not re.search(r"pytest\.mark\.skip\(|pytest\.skip\(", source), path.name
        if "skipif" in source:
            assert path.name == "test_cli_delivery.py", path.name
    assert "Some tests in `tests/test_cli_delivery.py` carry conditional skip markers" in README


def test_the_worded_test_count_gap_is_still_open():
    """The README lists this under Known defects. When the gap is closed, delete this test and that README line together."""
    assert check_test_claims("ninety tests pass.") == []
    assert "ninety tests pass" in section("## Known defects (open)")
    assert [d.kind for d in check_test_claims("999 tests pass.")] == ["tests"]
