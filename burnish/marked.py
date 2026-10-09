"""The one place Burnish is allowed to write in a README: between its own markers.

Burnish's generated section is wrapped like this (both lines are HTML comments,
invisible when the Markdown is shown):

    <!-- burnish:begin claims-vs-reality -->
    ...generated...
    <!-- burnish:end -->

Three rules follow from that, and every other module relies on them:

  * Burnish only ever replaces text between its markers. Anything else in the
    README, including a hand-written section with a similar heading, is the
    author's and is never touched.
  * The critic and every check read the README with the marked block removed
    (`without_block`), so Burnish never reads its own earlier output. That is
    what makes running it twice on its own result change nothing.
  * Markers inside a fenced code block are examples, not markers, and a `##`
    inside a fence is not a heading.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator, Optional

__all__ = ["BEGIN", "END", "HEADING", "Block", "find_block", "without_block", "outside_fences",
           "has_heading", "wrap", "unclosed_fence"]

BEGIN = "<!-- burnish:begin claims-vs-reality -->"
END = "<!-- burnish:end -->"
HEADING = "## Measured facts (generated)"

_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


@dataclass(frozen=True)
class Block:
    """Where the generated block sits in a README, or what is wrong with the markers."""

    start: int = -1   # character offset of the begin marker line
    end: int = -1     # character offset just past the end marker line (and its line break)
    problem: str = ""  # non-empty: the markers are not a single clean pair, so nothing may be edited

    @property
    def found(self) -> bool:
        return self.start >= 0


def outside_fences(text: str) -> Iterator[tuple[int, str]]:
    """(character offset, line without its line break) for each line that is not inside a fenced code block.

    The fence lines themselves are left out too.
    """
    fence = ""
    offset = 0
    for raw in text.splitlines(keepends=True):
        line = raw.rstrip("\r\n")
        opening = _FENCE.match(line)
        if fence:
            if opening and opening.group(1)[0] == fence[0] and len(opening.group(1)) >= len(fence) \
                    and not line.strip().strip(fence[0]):
                fence = ""
        elif opening:
            fence = opening.group(1)
        else:
            yield offset, line
        offset += len(raw)


def unclosed_fence(text: str) -> bool:
    """True when the text ends inside a fenced code block, where anything added at the end would become code."""
    fence = ""
    for raw in text.splitlines():
        opening = _FENCE.match(raw)
        if fence:
            if opening and opening.group(1)[0] == fence[0] and len(opening.group(1)) >= len(fence) \
                    and not raw.strip().strip(fence[0]):
                fence = ""
        elif opening:
            fence = opening.group(1)
    return bool(fence)


def _line_end(text: str, offset: int) -> int:
    """The offset just past the line that starts at `offset`, including its line break."""
    match = re.compile(r"\r\n|\n|\r").search(text, offset)
    return match.end() if match else len(text)


def find_block(text: str) -> Block:
    """The generated block in `text`, none, or a problem when the markers are unbalanced, repeated or reversed."""
    begins = [o for o, line in outside_fences(text) if line.strip() == BEGIN]
    ends = [o for o, line in outside_fences(text) if line.strip() == END]
    if not begins and not ends:
        return Block()
    if len(begins) != 1 or len(ends) != 1:
        return Block(problem="the Burnish markers are not a single begin and end pair")
    if ends[0] < begins[0]:
        return Block(problem="the Burnish end marker comes before its begin marker")
    return Block(start=begins[0], end=_line_end(text, ends[0]))


def without_block(text: str) -> str:
    """`text` with the generated block removed and the gap it leaves closed up, as the critic should read it.

    The result is the same whether or not the block was there, apart from the
    blank lines around it, so what is judged never depends on Burnish's last run.
    """
    block = find_block(text)
    if not block.found:
        return text
    before, after = text[:block.start].rstrip("\r\n\t "), text[block.end:].lstrip("\r\n")
    if not before:
        return after
    return before + ("\n\n" + after if after.strip() else "\n")


def has_heading(text: str, pattern: str) -> bool:
    """True when a real heading (not one inside a code fence) at level 2 or deeper matches `pattern`."""
    expression = re.compile(r"^#{2,6}[ \t]+(?:" + pattern + r")[ \t#]*$", re.I)
    return any(expression.match(line) for _, line in outside_fences(text))


def wrap(body: str) -> str:
    """The generated body inside its begin and end markers, with LF line breaks."""
    return f"{BEGIN}\n{HEADING}\n\n{body.strip()}\n{END}\n"
