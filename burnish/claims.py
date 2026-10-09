"""What a README says about its tests, found in its prose and checked against the measured suite.

Burnish never rewrites the author's sentences. It only reports where a number
or an absolute the author wrote does not match what Warden measured, or cannot
be matched to any measurement at all. Text inside code blocks and inline code
is not prose and is ignored, and so is the block Burnish generated itself.

It counts no tests. The measured numbers arrive as a `SuiteRun` from Warden.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from warden.suite import SuiteRun

from .marked import outside_fences, without_block
from .textsafe import clean

__all__ = ["TestClaim", "prose", "test_claims", "absolutes", "judge"]

_NUMBER = r"(\d{1,3}(?:,\d{3})+|\d+)"
_PASSING = r"(?:pass|passed|passing|passes|green)"
_NOT_A_THING = r"(?!\s+(?:files?|dirs?|directories|folders?|modules?|runners?|suites?|environments?|frameworks?|data|fixtures?|helpers?|harness))"
_PATTERNS = (
    ("passing", re.compile(rf"\b{_NUMBER}\s*/\s*{_NUMBER}\s+(?:tests?\s+)?{_PASSING}\b", re.I)),
    ("passing", re.compile(rf"\ball\s+{_NUMBER}\s+(?:\w+\s+)?tests?\b", re.I)),
    ("passing", re.compile(rf"\b{_NUMBER}\s+(?:\w+\s+)?tests?\s+(?:all\s+|are\s+|now\s+)?{_PASSING}\b", re.I)),
    ("count", re.compile(rf"\b{_NUMBER}\s+(?:(?!failing|failed|skipped|broken)\w+\s+)?tests?\b{_NOT_A_THING}", re.I)),
)
_LOWER_BOUND = re.compile(r"(?:at least|over|more than|above|\d\s*\+|plus)\s*$", re.I)
_ABSOLUTES = ("fully verified", "production ready", "battle tested", "100% coverage", "no known bugs")
_NEGATION = re.compile(r"\b(?:not|never|no longer|isn't|aren't|is not|are not|without|nor|n't)\W+(?:\w+\W+){0,3}$", re.I)


@dataclass(frozen=True)
class TestClaim:
    """One test-count claim in the README: the words, the number, and whether it says the tests pass."""

    __test__ = False  # not a pytest test class, whatever its name says

    text: str
    number: int
    kind: str          # "passing" (says they pass) or "count" (only says how many exist)
    at_least: bool = False
    total: Optional[int] = None


def prose(readme_text: str) -> str:
    """The README as plain prose: Burnish's own block, fenced code and inline code removed."""
    kept = without_block(readme_text)
    lines = [line for _, line in outside_fences(kept)]
    return re.sub(r"`[^`\n]*`", " ", "\n".join(lines))


def _int(raw: str) -> int:
    return int(raw.replace(",", ""))


def test_claims(readme_text: str) -> list[TestClaim]:
    """Each distinct test-count claim in the README prose, in the order it first appears."""
    text = prose(readme_text)
    found: dict[int, tuple[int, TestClaim]] = {}
    for kind, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            number = _int(match.group(1))
            total = _int(match.group(2)) if match.lastindex and match.lastindex >= 2 else None
            lower = bool(_LOWER_BOUND.search(text[max(0, match.start() - 12):match.start()]))
            claim = TestClaim(clean(match.group(0), 80), number, kind, lower, total)
            earlier = found.get(number)
            if earlier is None or (kind == "passing" and earlier[1].kind == "count"):
                found[number] = (min(match.start(), earlier[0]) if earlier else match.start(), claim)
    return [claim for _, claim in sorted(found.values(), key=lambda item: item[0])]


def absolutes(readme_text: str) -> list[str]:
    """Absolute claims no measurement can back ("fully verified", "production ready", ...), as the author wrote them."""
    text = prose(readme_text)
    out: list[str] = []
    for phrase in _ABSOLUTES:
        pattern = re.compile(r"\b" + r"[\s-]+".join(map(re.escape, phrase.split())) + r"\b", re.I)
        for match in pattern.finditer(text):
            if not _NEGATION.search(text[max(0, match.start() - 40):match.start()]):
                out.append(clean(match.group(0), 60))
                break
    return out


def judge(claim: TestClaim, suite: Optional[SuiteRun]) -> tuple[bool, str]:
    """(agrees, plain sentence) for one claim against the measured suite, or the plain statement that it is unmeasured."""
    if suite is None or not suite.ran:
        return False, (f"The README says {claim.number} tests; this number is unmeasured "
                       "because the test suite did not run.")
    seen = suite.passed
    everything = seen + suite.failed + suite.errors + suite.skipped + suite.xfailed + suite.xpassed
    if claim.at_least:
        agrees = seen >= claim.number
    elif claim.kind == "passing":
        agrees = seen == claim.number and (claim.total is None or claim.total == everything)
    else:
        agrees = claim.number in (seen, everything)
    verb = "agree" if agrees else "disagree"
    return agrees, (f"The README says {claim.number} tests; the measured suite has {seen} passing. "
                    f"These {verb}.")
