"""Census: README sentences that sound like a claim of a known class, found by word lists, so that silence is visible.

The 0.5.11 Warden miss had one root cause: the README said the program needs Warden, no check had a claim type for that,
and the report said nothing about the sentence. A check can only read the shapes it knows. The census is the other half:
it lists every present-tense sentence that sounds like a claim of one of these classes, so the critic can say which ones
no check read.

  * python-version: "works on Python 3.9 or newer", "Python 3.11+"
  * platform: "runs on Linux, macOS and Windows", "Windows is not supported"
  * performance: "it is fast", "starts in under 50 ms", "scales to millions"
  * security: "secure by design", "sandboxed", "encrypted at rest"
  * compatibility: "fully compatible with the 0.x API", "a drop-in replacement"
  * feature-completion: "all features are complete", "fully implemented"
  * build-deploy: "deploys to AWS with one command", "builds in Docker"
  * coverage: "80% branch coverage"

A sentence is listed only when it holds a word of a class and a claim verb ("is", "runs", "supports", ...). It is left out
when it is a heading, history ("before 0.3, it ran on 3.8", a dated statement), a wish or a rule ("we plan to support",
"should run"), or reported speech ("the old README claimed"); quoted words are not read. A denial ("Windows is not
supported") is listed: it is a claim too.

WHAT IT DOES NOT OWN
    Understanding. It matches words, so it lists some sentences that are not claims and misses claims written in other
    words. It decides nothing: whether a check read the sentence is the critic's business, and nothing it lists changes
    an outcome.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .identify import _HISTORY, _QUOTED, _WISH, _YEAR
from .sentences import pieces

__all__ = ["Mention", "claim_like", "KINDS"]


@dataclass(frozen=True)
class Mention:
    """One claim-like sentence: its words, the classes it sounds like, and the lines it spans (counting from 1)."""

    words: str
    kinds: tuple[str, ...]
    line: int
    end: int


_CLASSES: dict[str, re.Pattern[str]] = {
    "python-version": re.compile(r"\bpython\s*(?:[23](?:\.\d+)*\+?|versions?)(?!\w)|\bpy3\d{1,2}\b|\bcpython\b", re.I),
    "platform": re.compile(r"\b(?:windows|macos|mac\s+os|os\s*x|linux|posix|unix|freebsd|wsl)\b", re.I),
    "performance": re.compile(r"\b(?:fast|faster|fastest|quick|quickly|blazing|lightweight|efficient|performant|"
                              r"high-performance|low[- ]latency|scales?|scalable|\d+(?:\.\d+)?\s?(?:ms|milliseconds|"
                              r"µs|microseconds)|\d+x\s+faster|times\s+faster)\b", re.I),
    "security": re.compile(r"\b(?:secure|securely|security|safe|safely|sandbox(?:ed)?|encrypt\w*|vulnerab\w*|hardened|"
                           r"tamper\w*)\b", re.I),
    "compatibility": re.compile(r"\b(?:compatible|compatibility|backwards?|drop-in|breaking)\b", re.I),
    "feature-completion": re.compile(r"\b(?:complete|completed|finished|feature-complete|fully\s+implemented|"
                                     r"all\s+features)\b", re.I),
    "build-deploy": re.compile(r"\b(?:deploy\w*|docker\w*|kubernetes|one\s+command)\b", re.I),
    "coverage": re.compile(r"\bcoverage\b", re.I),
}
KINDS = tuple(_CLASSES)

_CLAIM_VERB = re.compile(r"\b(?:is|are|isn't|aren't|runs?|works?|supports?|supported|tested|ships?|deploys?|builds?|"
                         r"starts?|handles?|scales?|has|have|gives?|keeps?|stays?|remains?|passes|covers?|reaches?|"
                         r"installs?|needs?|requires?|uses?|targets)\b", re.I)
_REPORTED = re.compile(r"\b(?:said|claimed|stated|wrote|reported|read|according\s+to)\b", re.I)
_WORD = re.compile(r"[A-Za-z0-9_']+")
_LONGEST = 160


def claim_like(readme_text: str) -> list[Mention]:
    """Every claim-like sentence of the README prose, in order (lines are those of `readme_text`)."""
    every = list(pieces(readme_text))
    out = []
    for i, piece in enumerate(every):
        if piece.heading:
            continue
        text = _QUOTED.sub(" ", piece.text)
        if not _CLAIM_VERB.search(text) or _REPORTED.search(text) or _not_now(text):
            continue
        kinds = tuple(kind for kind, pattern in _CLASSES.items() if pattern.search(text))
        if not kinds:
            continue
        following = next((p.line for p in every[i + 1:] if p.line > piece.line), None)
        end = following - 1 if following is not None else piece.line
        end = max(piece.line, _last_text_line(readme_text, piece.line, end))
        words = piece.text if len(piece.text) <= _LONGEST else piece.text[:_LONGEST - 3] + "..."
        out.append(Mention(words, kinds, piece.line, end))
    return out


def _not_now(text: str) -> bool:
    """True for history or a dated statement, and for a wish, a goal or a rule: not a claim about the program now."""
    words = [w.lower() for w in _WORD.findall(text)]
    return any(w in _HISTORY or w in _WISH or _YEAR.match(w) for w in words)


def _last_text_line(text: str, start: int, end: int) -> int:
    """The last line from `start` to `end` that is not blank: the sentence ends there, not on the blank line after it."""
    lines = text.split("\n")
    for number in range(min(end, len(lines)), start - 1, -1):
        if lines[number - 1].strip():
            return number
    return start
