"""The generated README section states no number that drifts with the target.

Found by running the whole circuit over the circuit's own repositories: Burnish wrote the suite's pass count into the
README ("Warden ran the target's suite at the end of the loop: 1374 passed, ..."). SWIZZLE and JUDGE each have a test that
fails on a pass count in their README, so the finishing change broke their suites, Warden put it back, and the finisher
could never finish either repository. The four that did ACCEPT kept a number that goes stale at the next new test.

Every figure below is a snapshot: the suite's counts, how many findings Ghost still reports, how many change cycles ran, how
many files import a module, the size of the README going into the finish. What does not drift stays: what was checked, which
checks never ran, the decision, and the kinds of finding that remain.
"""

import re
from pathlib import Path

import pytest
from cns.defect import Defect, DefectSeverity
from cns.seat import Facts
from cns.suite import SuiteRun

from burnish.finisher import Burnish
from burnish.marked import BEGIN, END

#: The one number the generated section may repeat: the README's own claim, which the author already wrote.
AUTHORS_COUNT = "999"
#: A standalone number: not part of a word, a path, a version or an identifier.
STANDALONE_NUMBER = re.compile(r"(?<![\w./+-])\d[\d,]*(?![\w./+-])")
#: A version or a commit, which move with the target's pins.
VERSION_OR_COMMIT = re.compile(r"\bv?\d+\.\d+(?:\.\d+)?\b|\b(?=[0-9a-f]*\d)[0-9a-f]{7,40}\b")

PYPROJECT = """[project]
name = "demo"
version = "0.0.1"
description = "demo"
dependencies = [
    "warden @ git+https://github.com/example/Warden.git@9ecd1124e6c1b1c4ad7daed37b17f9009662dd9d",  # Warden 0.13.10, not tagged
    "cns @ git+https://github.com/example/CNS.git@v2.3.0",
]
"""
SOURCE = '"""demo."""\n\nimport cns\nimport warden\n\nVALUE = 1\n'
#: A README that gives the critic things to say: its own count, a pin the tree does not have, a dependency claim the imports
#: contradict, a long first sentence, a code block with no language, and enough lines to need a table of contents.
README = (
    "# demo\n\n"
    "A demonstration package with a one line description that is deliberately longer than a hundred and twenty characters "
    "so that the README critic has a length to report.\n\n"
    "Demo is pinned to Warden v0.1.0. It has no other dependencies. The suite has 999 tests.\n\n"
    "```\nbare fence\n```\n\n" + "\n".join(f"Line {n} of filler." for n in range(130)) + "\n"
)


def _facts(**suite_fields) -> Facts:
    many = tuple(Defect(ghost_id=f"ghost-{n}", summary=f"finding {n}", severity=DefectSeverity.LOW,
                        detector=("long_function" if n % 3 else "intra_function_duplicate_block")) for n in range(9))
    return Facts(suite=SuiteRun(**suite_fields), remaining=many, cycles=3)


GREEN = dict(ran=True, passed=1374, failed=0, errors=0, skipped=5, xfailed=2, xpassed=1, exit_code=0)
RED = dict(ran=True, passed=1370, failed=3, errors=1, skipped=5, xfailed=2, xpassed=1, exit_code=1)


def _block(root: Path, facts: Facts, readme: str = README) -> str:
    """The generated section the finisher would write into a demo tree's README, for these facts."""
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "__init__.py").write_text(SOURCE, encoding="utf-8")
    (root / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
    (root / "README.md").write_text(readme, encoding="utf-8")
    proposal = Burnish().finish(root, "base", facts)
    assert proposal is not None
    new = next(edit for edit in proposal.edits if edit.path == "README.md").new
    return new.split(BEGIN)[1].split(END)[0]


@pytest.mark.parametrize("suite", [GREEN, RED], ids=["green suite", "red suite"])
def test_the_section_states_no_count_of_the_suite(tmp_path: Path, suite: dict):
    block = _block(tmp_path, _facts(**suite))
    assert not re.search(r"\d[\d,]*\s+(?:passed|passing|failed|errors?|skipped|xfailed|xpassed)\b", block), block
    assert "1374" not in block and "1370" not in block


def test_the_section_states_no_count_of_ghost_findings_or_change_cycles(tmp_path: Path):
    block = _block(tmp_path, _facts(**GREEN))
    assert not re.search(r"\d+\s+(?:finding|change cycle)", block), block
    assert "long_function" in block and "intra_function_duplicate_block" in block


@pytest.mark.parametrize("suite", [GREEN, RED], ids=["green suite", "red suite"])
def test_the_section_carries_no_number_that_drifts_with_the_target(tmp_path: Path, suite: dict):
    """Whatever the facts and the README, the only figure left is the one the README's own author wrote."""
    block = _block(tmp_path, _facts(**suite))
    stray = [n for n in STANDALONE_NUMBER.findall(block) if n != AUTHORS_COUNT]
    assert stray == [], f"{stray} in:\n{block}"
    assert VERSION_OR_COMMIT.findall(block) == [], f"{VERSION_OR_COMMIT.findall(block)} in:\n{block}"


def test_what_does_not_drift_is_still_said(tmp_path: Path):
    block = _block(tmp_path, _facts(**GREEN))
    assert "Warden ran the target's suite" in block
    assert "not that Ghost is silent" in block
    assert "The README says a count of 999" in block and "These disagree." in block


def test_a_green_suite_is_said_to_be_green_and_a_red_one_is_said_not_to_be(tmp_path: Path):
    assert "green" in _block(tmp_path / "a", _facts(**GREEN))
    assert "not green" in _block(tmp_path / "b", _facts(**RED))


# ---- what the other repositories forbid in a README ----------------------------------------------------------------------
#
# Every pattern below is copied from a test in a sibling repository that fails when its README matches. Nothing is imported
# from them. The section Burnish writes lands in those READMEs, so it must match none of them, or the finishing change turns
# that repository's suite red and Warden puts it back (a FINISH_REJECTED the circuit could never get past).

FORBIDDEN = {
    # SWIZZLE Tests/test_ci_config.py::test_readme_does_not_hard_code_a_pass_count
    "a pass count (SWIZZLE)": re.compile(r"\b\d[\d,]*\s+passed\b"),
    # JUDGE tests/test_docs_claims.py::test_no_document_hardcodes_a_test_count_or_a_pin
    "a test count (JUDGE)": re.compile(r"\b\d{2,4} (tests|passed)\b"),
    "a pinned commit (JUDGE, DRAFTER)": re.compile(r"\b[0-9a-f]{40}\b"),
    "a Warden version (JUDGE)": re.compile(r"Warden (tag )?`?v\d+\.\d+\.\d+"),
    # ASSAY tests/test_docs_claims.py::test_readme_does_not_quote_a_test_count
    "a pass count (ASSAY)": re.compile(r"\b\d+\s+(passed|tests?\s+pass)"),
    # DRAFTER tests/test_release.py::test_the_readme_hard_codes_no_test_totals
    "a test total (DRAFTER)": re.compile(r"\b\d+\s+(?:full-gate\s+|real-Ghost\s+)?tests?\b"),
    # DRAFTER tests/test_release.py::test_the_readme_install_section_makes_no_false_commit_claim (its install section), applied to the
    # whole section here
    "a short commit (DRAFTER)": re.compile(r"\b(?=[0-9a-f]*\d)[0-9a-f]{7,40}\b"),
    # WARDEN tests/test_docs.py::test_the_readme_states_no_test_count_that_could_drift
    "a test count (WARDEN)": re.compile(r"\b\d[\d,]* tests (are|were|pass|collected)"),
    # ghost_tools Tests/test_docs_claims.py (the numbers it holds the README to)
    "a Python file count (ghost_tools)": re.compile(r"(\d[\d,]*) Python files"),
    "a detector count (ghost_tools)": re.compile(r"all (\d+) detectors"),
    "a version line (ghost_tools)": re.compile(r"Version (\d+\.\d+\.\d+) \(`pyproject.toml`"),
    # SWIZZLE Tests/test_readme_claims.py::test_the_readme_does_not_say_whether_tags_exist
    "a tag claim (SWIZZLE)": re.compile(r"\b(not tagged|no tags?|is tagged|are tagged yet|tag exists)\b", re.I),
    # JUDGE tests/test_readme_ledger.py::test_the_readme_does_not_say_whether_release_tags_exist
    "a tag claim (JUDGE)": re.compile(r"\b(?:not tagged|untagged|no tags?|tags? exists?|tags? do(?:es)? not)\b", re.I),
    # WATCHER_MCU tests/test_readme_ledger.py::test_the_readme_does_not_say_whether_release_tags_exist
    "a tag claim (WATCHER_MCU)": re.compile(r"(?i)\b(no release|no tag|not tagged|tags? exist)"),
    # ghost_tools Tests/test_docs_claims.py::test_the_readme_and_changelog_say_truthfully_what_is_tagged
    "a tag claim (ghost_tools)": re.compile(r"no release has been tagged|not tagged yet", re.I),
    # ghost_tools Tests/test_docs_claims.py::test_no_document_calls_cns_private and SWIZZLE
    # Tests/test_docs_install_hints.py::test_no_doc_calls_cns_private
    "CNS called private": re.compile(
        r"private\s+`?CNS|CNS\s*\(private\)|CNS is private|CNS`? is a private|cns \(private|private cns", re.I),
    # SWIZZLE Tests/test_docs_install_hints.py::test_no_user_facing_install_hint_names_a_bare_pypi_distribution_of_this_stack
    "a bare install of a stack name": re.compile(
        r"pip3?\s+install\s+(?:-\S+\s+)*[\"']?(swizzle|cns|warden|ghost_tools|ghost-tools|ghost_buster|assay|assay_production|judge"
        r"|drafter|burnish|watcher_mcu|watcher-mcu)\b(?!\s*@\s*git\+)", re.I),
    # SWIZZLE Tests/test_readme_claims.py::test_the_readme_uses_none_of_the_banned_words_and_no_em_dash, JUDGE
    # tests/test_readme_ledger.py::test_the_readme_and_changelog_use_no_em_dash, WARDEN tests/test_docs.py::test_no_document_uses_an_em_dash
    "an em or en dash": re.compile("[\u2014\u2013]"),
    # the marketing-word list the siblings' README tests share (SWIZZLE test_readme_claims.py BANNED, JUDGE test_readme_ledger.py
    # BANNED_WORDS, ghost_tools test_docs_claims.py _MARKETING_WORDS)
    "a marketing word": re.compile(r"robust|powerful|production-ready|production ready|seamless|comprehensive|blazing|enterprise"
                                   r"|battle-tested|state-of-the-art", re.I),
    # DRAFTER tests/test_release.py::test_the_readme_does_not_restate_the_pinned_versions
    "a stale pin sentence (DRAFTER)": re.compile(r"pinned to Warden tag|v0\.11|0\.11\.5"),
    # what the first test in this file already holds: no version of anything the target pins
    "a version or commit (all)": VERSION_OR_COMMIT,
}

#: The line Burnish wrote before this change, from a real run over SWIZZLE. Every pattern set above must be able to fail.
THE_LINE_THAT_BROKE_SWIZZLE = ("- Warden ran the target's suite at the end of the loop: 1374 passed, 0 failed, 0 errors, 5 skipped, "
                               "0 xfailed, 0 xpassed.")

BROKEN_LINKS = "# demo\n\nA short demonstration.\n\nSee [the guide](docs/guide1.md) and [more](docs/guide2.md).\n"
FACTS_BY_CASE = {
    "green suite": (_facts(**GREEN), README),
    "red suite": (_facts(**RED), README),
    "suite that did not run": (Facts(suite=SuiteRun(ran=False, reason="pytest was not found"), remaining=(), cycles=0,
                                     unmeasured=("ghost", "suite")), README),
    "no findings, links that do not resolve": (Facts(suite=SuiteRun(ran=True, passed=5, exit_code=0), remaining=(), cycles=1),
                                               BROKEN_LINKS),
}


def test_the_patterns_are_able_to_fail():
    hit = [name for name, pattern in FORBIDDEN.items() if pattern.search(THE_LINE_THAT_BROKE_SWIZZLE)]
    assert "a pass count (SWIZZLE)" in hit and "a test count (JUDGE)" in hit and "a pass count (ASSAY)" in hit, hit


@pytest.mark.parametrize("case", list(FACTS_BY_CASE))
def test_the_section_matches_nothing_a_sibling_repository_forbids_in_a_readme(tmp_path: Path, case: str):
    facts, readme = FACTS_BY_CASE[case]
    block = _block(tmp_path, facts, readme)
    tripped = {name: pattern.findall(block) for name, pattern in FORBIDDEN.items() if pattern.search(block)}
    assert tripped == {}, f"{tripped} in:\n{block}"
