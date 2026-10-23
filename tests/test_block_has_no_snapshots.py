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
    "warden @ git+https://github.com/example/Warden.git@b57b81e1c98333c43d422666c89a8fcf3ae6eaca",  # Warden 0.13.9, not tagged
    "cns @ git+https://github.com/example/CNS.git@v2.0.0",
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


def _block(root: Path, facts: Facts) -> str:
    """The generated section the finisher would write into a demo tree's README, for these facts."""
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "__init__.py").write_text(SOURCE, encoding="utf-8")
    (root / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
    (root / "README.md").write_text(README, encoding="utf-8")
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
