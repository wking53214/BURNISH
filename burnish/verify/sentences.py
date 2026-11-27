"""Extraction: the README as pieces of prose, each with its line and the structure it sits in.

A piece is one sentence of a paragraph, one heading, or one cell of a table row. Code (fenced, indented), HTML comments and
Burnish's own block are removed first by `burnish.marked.prose_lines`. Inline code keeps its words, without the backticks:
a package name is often written as code. A link keeps its text and loses its address.

WHAT IT DOES NOT OWN
    Deciding what a piece means. It only cuts the README up and says where each piece came from.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator

from ..marked import prose_lines

__all__ = ["Piece", "pieces"]


@dataclass(frozen=True)
class Piece:
    """One sentence, heading or table cell, and the README line it starts on (counting from 1)."""

    text: str
    line: int
    heading: bool = False
    table: bool = False
    blockquote: bool = False


_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[\"'(\[A-Z0-9`])")
_HEADING = re.compile(r"^ {0,3}#{1,6}\s+")
_QUOTE = re.compile(r"^ {0,3}>\s?")
_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")


def _plain(line: str) -> str:
    return _LINK.sub(r"\1", line).replace("`", "").replace("**", "").replace("__", "")


def pieces(readme_text: str) -> Iterator[Piece]:
    """Every piece of the README's prose, in order."""
    paragraph: list[tuple[int, str]] = []
    quoted = False
    for number, raw in prose_lines(readme_text) + [(0, "")]:
        line = _plain(raw)
        if _HEADING.match(line):
            yield from _sentences(paragraph, quoted)
            paragraph = []
            yield Piece(_HEADING.sub("", line).strip(" #"), number, heading=True)
            continue
        if line.lstrip().startswith("|"):
            yield from _sentences(paragraph, quoted)
            paragraph = []
            for cell in line.strip().strip("|").split("|"):
                if cell.strip() and not set(cell.strip()) <= set("-: "):
                    yield Piece(cell.strip(), number, table=True)
            continue
        blockquote = bool(_QUOTE.match(line))
        line = _QUOTE.sub("", line)
        if not line.strip() or _ITEM.match(line) or blockquote != quoted:
            yield from _sentences(paragraph, quoted)
            paragraph = []
        quoted = blockquote
        if line.strip():
            paragraph.append((number, _ITEM.sub("", line).strip()))


def _sentences(paragraph: list[tuple[int, str]], blockquote: bool) -> Iterator[Piece]:
    """The sentences of one paragraph, each with the line it starts on."""
    if not paragraph:
        return
    text, starts = "", []
    for number, line in paragraph:
        starts.append((len(text), number))
        text += line + " "
    begin = 0
    for match in list(_SENTENCE_END.finditer(text)) + [None]:
        end = match.start() if match else len(text)
        sentence = text[begin:end].strip()
        if sentence:
            first = max((n for offset, n in starts if offset <= begin), default=paragraph[0][0])
            yield Piece(sentence, first, blockquote=blockquote)
        if match:
            begin = match.end()
