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
  * Markers inside a fenced code block, an indented code block or an HTML comment
    are examples or hidden text, not markers, and a `##` inside any of them is
    not a heading. A marker must start within three columns of the margin.
  * A README that ends inside an unclosed HTML comment hides everything that
    follows, so `ends_inside_comment` tells the caller to close it first.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator, Optional

__all__ = ["BEGIN", "END", "HEADING", "Block", "find_block", "without_block", "outside_fences",
           "has_heading", "wrap", "unclosed_fence", "ends_inside_comment"]

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


_LIST_ITEM = re.compile(r"^ {0,3}(?:[-*+]|\d{1,9}[.)])(?:\s|$)")
_BLOCK_LINE = re.compile(r"^ {0,3}(?:#{1,6}(?:\s|$)|(?:[-*_][ \t]*){3,}$)")


def _indent(line: str) -> int:
    """Columns of white space at the start of `line`, a tab counting as four."""
    columns = 0
    for char in line:
        if char == " ":
            columns += 1
        elif char == "\t":
            columns += 4 - columns % 4
        else:
            break
    return columns


def _raw_lines(text: str) -> list[str]:
    """The lines of `text` with their breaks kept, splitting only on CRLF, LF and CR (not on form feeds)."""
    return re.findall(r"[^\r\n]*(?:\r\n|\n|\r)|[^\r\n]+$", text)


def _classify(text: str) -> tuple[list[tuple[int, str, str]], str]:
    """(offset, line without its break, kind) for every line, and what the text ends inside.

    kind is one of "text", "blank", "html1" (a one-line HTML comment, which is where the
    markers live), "comment" (a line of a multi-line HTML comment), "fence" (a fenced
    code line, fence lines included) or "indented" (an indented code block). The second
    value is "fence", "comment" or "" for the state at the end of the text.
    """
    out: list[tuple[int, str, str]] = []
    fence, comment = "", False
    previous, in_list, after_block, offset = "blank", False, False, 0
    for raw in _raw_lines(text):
        line = raw.rstrip("\r\n")
        opening = _FENCE.match(line)
        if fence:
            kind = "fence"
            if opening and opening.group(1)[0] == fence[0] and len(opening.group(1)) >= len(fence) \
                    and not line.strip().strip(fence[0]):
                fence = ""
        elif comment:
            kind = "comment"
            comment = "-->" not in line or line.strip() in {BEGIN, END}
        elif not line.strip():
            kind = "blank"
        elif opening:
            kind, fence = "fence", opening.group(1)
        elif _indent(line) <= 3 and line.lstrip().startswith("<!--"):
            start = line.index("<!--")
            closed = line.find("-->", start + 2) >= 0
            kind, comment = ("html1", False) if closed else ("comment", True)
        else:
            kind = "text"
            if _LIST_ITEM.match(line):
                in_list = True
            elif _indent(line) < 2 and previous == "blank":
                in_list = False
            if _indent(line) >= 4 and not in_list and (previous in {"blank", "indented", "fence", "html1"}
                                                      or (previous == "text" and after_block)):
                kind = "indented"
        after_block = kind == "text" and bool(_BLOCK_LINE.match(line))
        out.append((offset, line, kind))
        previous = kind
        offset += len(raw)
    return out, ("fence" if fence else "comment" if comment else "")


def outside_fences(text: str) -> Iterator[tuple[int, str]]:
    """(character offset, line without its line break) for each line that is prose.

    Lines inside a fenced code block (fence lines included), an indented code block or an
    HTML comment are left out. The name is older than the other exclusions.
    """
    for offset, line, kind in _classify(text)[0]:
        if kind in {"text", "blank"}:
            yield offset, line


def unclosed_fence(text: str) -> bool:
    """True when the text ends inside a fenced code block, where anything added at the end would become code."""
    return _classify(text)[1] == "fence"


def ends_inside_comment(text: str) -> bool:
    """True when the text ends inside an HTML comment that was opened and never closed.

    Everything after such an opener is hidden, so a block added at the end would be hidden too.
    """
    return _classify(text)[1] == "comment"


def _line_end(text: str, offset: int) -> int:
    """The offset just past the line that starts at `offset`, including its line break."""
    match = re.compile(r"\r\n|\n|\r").search(text, offset)
    return match.end() if match else len(text)


def find_block(text: str) -> Block:
    """The generated block in `text`, none, or a problem when the markers are unbalanced, repeated or reversed."""
    lines = [(o, line) for o, line, kind in _classify(text)[0]
             if kind in {"text", "html1"} and _indent(line) <= 3]
    begins = [o for o, line in lines if line.strip() == BEGIN]
    ends = [o for o, line in lines if line.strip() == END]
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
