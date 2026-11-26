"""What a README says about its tests, found in its prose and checked against the measured suite.

Burnish never rewrites the author's sentences. It only reports where a number
or an absolute the author wrote does not match what Warden measured, or cannot
be matched to any measurement at all. Text inside code blocks, indented code,
HTML comments and inline code is not prose and is ignored, and so is the block
Burnish generated itself.

ONLY CLAIMS ABOUT THIS PROJECT'S OWN SUITE ARE JUDGED

"All 30 tests pass", "30/30 passing", "the suite has 30 tests" and "100% coverage"
(said bare, as a fact) are claims. These are not, and are never judged:

  * a change or a history: "added 5 tests", "went from 255 to 272 tests",
    "before the fix, 10 tests failed", "there were 30 tests in v1",
  * another thing's count: a version ("Python 3.11 tests"), a subset ("12 unit
    tests"), a table row about something else, a file ("test_x.py has 3 tests"),
    or a named subject ("herald 390 tests"). The last three are counted as
    "mentioned, not checked" so the report can say so without quoting them,
  * a wish, a rule or a denial: "should have 30 tests", "we make no claim of
    100% coverage", "the goal is 100% coverage",
  * a quotation: a phrase inside double quotation marks is mentioned, not asserted.

Some words that usually deny, wish or look back do not here: "not just fast but production ready", "without exception, all
30 tests pass", "if you clone it, all 30 tests pass", "as of today, the suite has 30 tests" and "the suite was rewritten; it
now has 30 tests" are claims. A table cell ends a count ("| Tests | 40 tests |"), and a count after a named part ("the
parser module has 3 tests") is about that part.

The shapes mirror what Ghost Tools treats as not a current claim, copied here and
not imported: Burnish reads no other role's code.

It counts no tests. The measured numbers arrive as a `SuiteRun` from Warden.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator, Optional

from cns.suite import SuiteRun

from .marked import prose_lines
from .textsafe import clean

__all__ = ["TestClaim", "prose", "test_claims", "unchecked_mentions", "absolutes", "absolutes_at", "judge"]

#: What inline code becomes in the prose: its words are gone, but the claim next to it is still known to be about it.
_CODE = "\u2039code\u203a"
_UNITS = "two|three|four|five|six|seven|eight|nine"
_TEENS = "ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen"
_TENS = "twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety"
_BELOW_100 = rf"(?:(?:{_TENS})(?:[-\s](?:one|{_UNITS}))?|{_TEENS}|{_UNITS})"
#: Number words up to 999 ("twelve", "twenty-one", "two hundred and five"). Not "one" or "zero": they are too common in prose.
#: Not after "thousand", "million" or "hundred", so "one thousand three hundred and seventy four" is missed whole, never read as 74.
_AFTER_A_LARGER_WORD = r"(?<!thousand\s)(?<!million\s)(?<!hundred\s)(?<!hundred\sand\s)(?<!thousand\sand\s)"
_WORDS = (rf"{_AFTER_A_LARGER_WORD}(?:(?:one|a|{_UNITS})\s+hundred(?:\s+(?:and\s+)?(?:one|{_BELOW_100}))?|{_BELOW_100})")
#: A count as people write it: digits (a comma, dot, space, apostrophe, underscore or non-breaking space between groups of
#: three), a number of thousands ("1k", "1.4k"), or a number word.
_SEPARATORS = "[,.\u00a0\u202f\u2009' _]"
_NUMBER = (rf"(\d+(?:\.\d+)?[kK]\b|\d{{1,3}}(?:{_SEPARATORS}\d{{3}})+(?!\d)|\d+|{_WORDS})")
_PASSING = r"(?:pass|passed|passing|passes|green)"
_STANDALONE = r"(?<![\w.,/\-])"
_RATIO = re.compile(rf"{_STANDALONE}{_NUMBER}\s*/\s*{_NUMBER}\s+(?:tests?\s+)?{_PASSING}\b", re.I)
_COUNT = re.compile(
    rf"{_STANDALONE}(?P<all>all\s+)?{_NUMBER}\s+(?:(?P<q>[A-Za-z][\w-]*)\s+)?tests?(?:\s+cases?)?\b(?![\w/\-]|\.\w)", re.I)
_GREEN = re.compile(r"\ball\s+(?:of\s+)?(?:the\s+|our\s+|its\s+)?tests?\s+(?:are\s+|now\s+|currently\s+|all\s+)*"
                    rf"{_PASSING}\b", re.I)
#: Words that may sit between the number and "tests" and still leave it a count of the whole suite.
_WHOLE = frozenset({"automated", "total", "pytest", "passing", "passed", "green"})
_PASS_AFTER = re.compile(rf"^\s+(?:(?:all|are|now|currently)\s+)*{_PASSING}\b", re.I)
_TAIL = re.compile(r"^(?:[ \t]*(?:[,.;:)!|]|\n|$)|\s+(?:in\s+total|total|(?:are\s+)?collected|exists?|ran|runs?|covers?|covering|"
                   r"in\s+the\s+suite|in\s+this\s+repo\w*|and)\b)", re.I)
_LOWER_BOUND = re.compile(r"(?:at least|over|more than|above|\d\s*\+|plus)\s*$", re.I)
_NO_SKIPS = re.compile(r"\b(?:no|zero|without|never|0|none|nothing)\s+(?:tests?\s+)?(?:skips?|skipped|skipping)\b|"
                       r"\bskip-free\b|\bnone\s+(?:are\s+)?skipped\b", re.I)

# What makes a number-and-"tests" something other than a claim about the suite as it is now.
_DELTA = re.compile(r"\b(?:gained|gains|gain|added|adds|add|grew|grown|grows|growing|plus|minus|removed|removes|"
                    r"dropped|drops|another|extra|net|more|fewer)\b\s*(?:by\s+)?$", re.I)
_TRANSITION = re.compile(rf"(?:\bfrom\s+(?:\d[\d,. _]*|{_WORDS})\s+to\s+|\b\d+\s*(?:->|-->|→)\s*)$", re.I)
_QUOTATION = re.compile(r"[\"'“‘]\s*$")
_ATTRIBUTION = re.compile(r"\b(?:claimed|reported|said)\s*$", re.I)
_HISTORY = re.compile(r"\b(?:before|previously|formerly|used\s+to|once|originally|initially|earlier|prior\s+to|until|"
                      r"was|were|had|at\s+the\s+time|as\s+of|back\s+in|recorded|"
                      r"jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|20\d\d)\b", re.I)
_WISH = re.compile(r"\b(?:will|would|should|could|might|must|aim|aims|aiming|goal|goals|target|targets|plan|plans|"
                   r"planned|expect|expected|need|needs|want|wants|if|unless|whether|eventually|someday|ought|"
                   r"require|requires|required)\b", re.I)
_DENIAL = re.compile(r"\b(?:no|not|never|nor|without|isn't|aren't|don't|doesn't|cannot|can't)\b|n't\b", re.I)
_NO_CLAIM = re.compile(r"\b(?:no|not|never|without)\s+(?:\w+\s+){0,2}claims?\b|\bclaims?\s+(?:no|nothing)\b|"
                       r"\bdo(?:es)?\s+not\s+claim\b|\bdon't\s+claim\b|\bwithout\s+claiming\b", re.I)
# Burnish's copy of Ghost's "a bare word before the number names its owner" rule.
_OWNER = re.compile(r"(?:^|[\s(\[,;])([A-Za-z][\w.\-]*)\s+$")
_LEAD_INS = frozenset((
    "the a an its our their this these those my has have had is are was were be been of with and or to in at on by "
    "from about across than plus all only just now still over under some another roughly around nearly collects "
    "collected contains holds runs run ran adds added totals totalling totaling reaching reached leaving leaves "
    "comprising numbering counts gained gains gain grew grown grows growing minus removed removes dropped drops extra "
    "net more fewer claimed reported said currently presently there here we suite tests test total full entire whole "
    "every so ci pytest also now currently ships includes include including currently least above").split())
#: A named part before the count: "the parser module has 3 tests" counts one module, not the suite.
_NAMED_PART = re.compile(r"\b([A-Za-z][\w.\-]*)\s+(?=(?:module|package|subpackage|file|class|function|component|plugin|"
                         r"crate)\b)", re.I)
#: Phrases that hold a negative, wishful or past word and still state a claim about now. They are taken out of the
#: sentence before it is tested for a denial, a wish or a history: "without exception, all 30 tests pass" claims a count.
_NOT_DENYING = re.compile(r"\b(?:without\s+(?:exception|fail|doubt)|no\s+(?:doubt|surprise)|no\s+one\s+(?:disputes|doubts)|"
                          r"not\s+(?:just|only|merely|simply))\b", re.I)
_NOT_WISHING = re.compile(r"\b(?:if|when|once)\s+you\b[^,.;:]*,", re.I)
_NOT_PAST = re.compile(r"\bas\s+of\s+(?:today|now|this\s+(?:release|version|writing|commit))\b", re.I)
#: A word after a history word that brings the sentence back to now: "the suite was rewritten and now has 30 tests".
_NOW = re.compile(r"\b(?:now|currently|presently|today)\b", re.I)
_SCOPED_TO_FILE = re.compile(r"\b\w+\.py\b|\btests?/|\btest_\w+|--ignore|\bpytest\s+\S", re.I)

_ABSOLUTES = ("fully verified", "production ready", "battle tested", "100% coverage", "no known bugs")
_NEGATION = re.compile(r"\b(?:not|never|no longer|isn't|aren't|is not|are not|without|nor|n't)\W+(?:\w+\W+){0,3}$", re.I)
_SCOPED_COVERAGE = re.compile(r"^\s+(?:of|on|for|in|across|within|at|by)\b", re.I)
_AFTER_WISH = re.compile(r"^\W*(?:\w+\W+){0,3}?(?:goal|target|aim|aspiration|plan|someday|eventually|not\s+yet)\b", re.I)


@dataclass(frozen=True)
class TestClaim:
    """One claim about this suite in the README: the words, the number, and whether it says the tests pass."""

    __test__ = False  # not a pytest test class, whatever its name says

    text: str
    number: int
    kind: str          # "passing" (says they pass), "count" (only says how many exist) or "green" (all pass, no number)
    at_least: bool = False
    total: Optional[int] = None
    no_skips: bool = False   # the sentence says nothing was skipped
    #: The line of the README text it was read from, counting from 1 (0 when not known).
    line: int = 0


def prose(readme_text: str) -> str:
    """The README as plain prose: Burnish's own block, code (fenced, indented, inline) and HTML comments removed."""
    return _prose_and_lines(readme_text)[0]


def _prose_and_lines(readme_text: str) -> tuple[str, list[int]]:
    """The prose, and for each of its lines the number of the README line it came from."""
    kept = prose_lines(readme_text)
    return re.sub(r"`[^`\n]*`", _CODE, "\n".join(line for _, line in kept)), [number for number, _ in kept]


def _line_at(text: str, lines: list[int], offset: int) -> int:
    """The README line that `offset` in the prose `text` came from, or 0."""
    index = text.count("\n", 0, offset)
    return lines[index] if index < len(lines) else 0


_WORD_VALUES = {word: value for value, word in enumerate(
    ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen",
     "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"))}
_WORD_VALUES.update({word: 20 + 10 * step for step, word in enumerate(
    ("twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"))})


def _words_to_int(raw: str) -> int:
    """"twenty-one" is 21, "two hundred and five" is 205, "a hundred" is 100."""
    total = 0
    pieces = re.split(r"[-\s]+", raw.lower())
    for index, piece in enumerate(pieces):
        if piece == "and":
            continue
        if piece == "hundred":
            total = (total or 1) * 100
        elif piece == "a":
            total = 1
        else:
            total += _WORD_VALUES[piece]
        del index
    return total


def _int(raw: str) -> int:
    """The number a count was written as: "1,374", "1.374", "1 374", "1k", "twelve"."""
    if raw[-1] in "kK" and raw[0].isdigit():
        return round(float(raw[:-1]) * 1000)
    if raw[0].isdigit():
        return int(re.sub(r"\D", "", raw))
    return _words_to_int(raw)


def _sentence(text: str, start: int) -> str:
    """The part of the sentence before `start`, which is what decides what a phrase means."""
    before = text[max(0, start - 200):start]
    return re.split(r"(?<=[.!?])\s+|\n\s*\n|\n[ \t]*(?:[-*+]|\d+[.)])\s", before)[-1]


def _sentence_after(text: str, end: int) -> str:
    after = text[end:end + 160]
    return re.split(r"(?<=[.!?])\s|\n\s*\n", after)[0]


def _line(text: str, start: int) -> tuple[str, int]:
    """The line holding `start`, and where in it `start` falls."""
    begin = text.rfind("\n", 0, start) + 1
    finish = text.find("\n", start)
    return text[begin:finish if finish >= 0 else len(text)], start - begin


def _clause(lead: str, marks: str = ";") -> str:
    """The last clause of `lead`: "the suite was rewritten; it now has" is read from "it now has"."""
    return re.split(rf"[{marks}]", lead)[-1]


def _looks_back(lead: str) -> bool:
    """True when the words before a phrase put it in the past, and nothing after the past word brings it back to now."""
    kept = _NOT_PAST.sub(" ", lead)
    found = list(_HISTORY.finditer(kept))
    return bool(found) and not _NOW.search(kept[found[-1].end():])


def _denies(lead: str) -> bool:
    """True when the clause right before a phrase denies it. A colon ends a clause here: "it is not small: it has"."""
    return bool(_DENIAL.search(_NOT_DENYING.sub(" ", _clause(lead, ":;"))[-60:]))


def _wishes(lead: str) -> bool:
    """True when the words before a phrase make it a wish, a goal or a condition. "If you clone it," is none of these."""
    return bool(_WISH.search(_NOT_WISHING.sub(" ", lead)))


def _quoted(text: str, start: int) -> bool:
    """True when the phrase sits inside double quotation marks on its line: it is mentioned or reported, not asserted."""
    line, at = _line(text, start)
    before, after = line[:at], line[at:]
    if "\u201c" in before and before.count("\u201c") > before.count("\u201d") and "\u201d" in after:
        return True
    return before.count('"') % 2 == 1 and '"' in after


def _not_a_claim(text: str, start: int, end: int) -> bool:
    """True for a phrase that is a change, a history, a wish, a denial or a quotation rather than a statement of the suite now."""
    before = text[max(0, start - 80):start]
    if _DELTA.search(before) or _TRANSITION.search(before) or _QUOTATION.search(before) \
            or _ATTRIBUTION.search(before) or _quoted(text, start):
        return True
    lead = _clause(_sentence(text, start))
    return bool(_looks_back(lead) or _wishes(lead) or _NO_CLAIM.search(lead) or _denies(lead))


def _scoped(text: str, start: int, end: int) -> bool:
    """True when the phrase counts something other than this whole suite: a named subject, a file, another table row."""
    line, at = _line(text, start)
    named = _OWNER.search(line[max(0, at - 80):at])
    if named and named.group(1).lower() not in _LEAD_INS:
        return True
    parts = list(_NAMED_PART.finditer(_clause(line[max(0, at - 80):at], ",:;")))
    if parts and parts[-1].group(1).lower() not in _LEAD_INS:
        return True
    if _SCOPED_TO_FILE.search(line[max(0, at - 60):at + (end - start) + 60]) or _CODE in line[max(0, at - 60):at]:
        return True
    if "|" in line:
        cells = [c for c in line.split("|")]
        position = line[:at].count("|")
        filled = [(i, c) for i, c in enumerate(cells) if c.strip()]
        if filled and position != filled[0][0] and not re.search(r"test|suite|status|result|passing|\bci\b",
                                                                filled[0][1], re.I):
            return True
    return False


def _candidates(text: str) -> Iterator[tuple[int, int, TestClaim, re.Match[str]]]:
    """Every phrase that could be a test-count claim: (start, end, claim or None, why-not-judged)."""
    for match in _RATIO.finditer(text):
        yield match.start(), match.end(), TestClaim(clean(match.group(0), 80), _int(match.group(1)), "passing",
                                                   False, _int(match.group(2))), match
    for match in _COUNT.finditer(text):
        qualifier = (match.group("q") or "").lower()
        if qualifier and qualifier not in _WHOLE:
            continue
        following = text[match.end():]
        says_pass = qualifier in {"passing", "passed", "green"} or bool(_PASS_AFTER.match(following))
        if not says_pass and not _TAIL.match(following):
            continue
        before = text[max(0, match.start() - 12):match.start()]
        kind = "passing" if says_pass else "count"
        yield match.start(), match.end(), TestClaim(clean(match.group(0), 80), _int(match.group(2)), kind,
                                                   bool(_LOWER_BOUND.search(before))), match
    for match in _GREEN.finditer(text):
        yield match.start(), match.end(), TestClaim(clean(match.group(0), 80), 0, "green"), match


def _read(readme_text: str) -> tuple[list[TestClaim], int]:
    """The claims about this suite, in order of appearance, and how many other mentions were not judged."""
    text, lines = _prose_and_lines(readme_text)
    found: dict[int, tuple[int, TestClaim]] = {}
    unchecked: set[int] = set()
    for start, end, claim, _ in _candidates(text):
        if _not_a_claim(text, start, end):
            continue
        if claim.kind != "green" and _scoped(text, start, end):
            unchecked.add(start)
            continue
        sentence = _sentence(text, start) + text[start:end] + _sentence_after(text, end)
        key = claim.number if claim.kind != "green" else -1
        earlier = found.get(key)
        first = min(start, earlier[0]) if earlier else start
        claim = TestClaim(claim.text, claim.number, claim.kind, claim.at_least, claim.total,
                          bool(_NO_SKIPS.search(sentence)), _line_at(text, lines, start))
        if earlier is None or (claim.kind == "passing" and earlier[1].kind == "count"):
            found[key] = (first, claim)
    return [claim for _, claim in sorted(found.values(), key=lambda item: item[0])], len(unchecked)


def test_claims(readme_text: str) -> list[TestClaim]:
    """Each distinct claim about this suite in the README prose, in the order it first appears."""
    return _read(readme_text)[0]


def unchecked_mentions(readme_text: str) -> int:
    """How many test counts the README mentions that are about something else (a file, a table row, a named subject).

    They are not judged against the suite, and the report says only how many there are, never the words.
    """
    return _read(readme_text)[1]


def absolutes(readme_text: str) -> list[str]:
    """Absolute claims no measurement can back ("fully verified", "production ready", ...), as the author wrote them.

    A denial ("not production ready", "we make no claim of 100% coverage"), a goal ("the target is 100%
    coverage") and a scoped figure ("100% coverage of the parser") are not claims of the whole being so.
    """
    return [phrase for phrase, _ in absolutes_at(readme_text)]


def absolutes_at(readme_text: str) -> list[tuple[str, int]]:
    """The same absolute claims as `absolutes`, each with the README line it is on (0 when not known)."""
    text, lines = _prose_and_lines(readme_text)
    out: list[tuple[str, int]] = []
    for phrase in _ABSOLUTES:
        words = r"[\s-]+".join(map(re.escape, phrase.split()))
        if phrase == "100% coverage":   # "100% test coverage", "100% line coverage" claim the same
            words = r"100%[\s-]+(?:(?:test|code|line|branch|statement)[\s-]+)?coverage"
        pattern = re.compile(r"\b" + words + r"\b", re.I)
        for match in pattern.finditer(text):
            lead = _clause(_sentence(text, match.start()))
            negation = _NEGATION.search(text[max(0, match.start() - 40):match.start()])
            if negation and _NOT_DENYING.search(negation.group(0)):
                negation = None   # "not just fast but production ready" still claims it
            if negation or _NO_CLAIM.search(lead) or _wishes(lead) or _quoted(text, match.start()) \
                    or _AFTER_WISH.match(_sentence_after(text, match.end())):
                continue
            if phrase.startswith("100%") and _SCOPED_COVERAGE.match(text[match.end():]):
                continue
            out.append((clean(match.group(0), 60), _line_at(text, lines, match.start())))
            break
    return out


def judge(claim: TestClaim, suite: Optional[SuiteRun]) -> tuple[bool, str]:
    """(agrees, plain sentence) for one claim against the measured suite, or the plain statement that it is unmeasured.

    Skipped tests are not failures: "30/30 passing" over 28 passed and 2 skipped agrees, with the skips named,
    unless the README says nothing is skipped. The sentence never repeats the README's number next to the word
    "tests", so Ghost Tools does not read the report as a new claim of its own, and it states none of the measured counts:
    a count is a snapshot that goes stale, and some repositories fail a README that carries one.
    """
    what = "that all tests pass" if claim.kind == "green" else f"a count of {claim.number}"
    if suite is None or not suite.ran:
        return False, f"The README says {what}; this is unmeasured because the test suite did not run."
    seen = suite.passed
    skipped = suite.skipped + suite.xfailed
    everything = seen + suite.failed + suite.errors + suite.skipped + suite.xfailed + suite.xpassed
    clean_run = suite.failed == 0 and suite.errors == 0
    if claim.kind == "green":
        agrees = clean_run and seen > 0 and not (claim.no_skips and skipped)
    elif claim.at_least:
        agrees = seen >= claim.number
    elif claim.kind == "passing":
        agrees = seen == claim.number and (claim.total is None or claim.total == everything)
        if not agrees and clean_run and skipped and not claim.no_skips:
            agrees = claim.number == everything and (claim.total is None or claim.total == everything)
    else:
        agrees = claim.number in (seen, everything)
    verb = "agree" if agrees else "disagree"
    measured = f"the measured suite {'matches' if agrees else 'does not match'} it"
    if skipped:
        measured += ", with some tests skipped or expected to fail"
    if suite.failed or suite.errors:
        measured += ", and some tests failed or errored"
    return agrees, f"The README says {what}; {measured}. These {verb}."
