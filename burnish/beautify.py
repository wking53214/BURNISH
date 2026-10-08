"""Behavior-preserving tidying of Python source.

Today this does one thing: it removes trailing whitespace and makes sure a
file ends in exactly one newline. That is the only beautification built so far;
`burnish languages` says what else is written down and not yet built.

THE GUARD

Lines whose break sits inside a multi-line string are never touched, because
trailing spaces there are part of the string. As a second, independent guard,
every tidied file is parsed before and after; if the two syntax trees differ at
all, the file is left alone. Nothing is ever guessed to be safe.

This module returns text. Writing it is Warden's job, behind a grant, a green
suite before and after, and a re-inspection by Ghost Tools.
"""

from __future__ import annotations

import ast
import io
import tokenize
from pathlib import Path
from typing import Iterator, Optional

from warden.models import FileEdit

_SKIPPED_DIRS = {".git", "__pycache__", ".venv", "venv", "build", "dist", ".pytest_cache",
                 "target", "node_modules", ".ruff_cache", ".mypy_cache", "site-packages"}


def tidy_source(source: str) -> Optional[str]:
    """The tidied text, or None if tidying would change the program or nothing needs tidying."""
    if not source.strip():
        return None
    try:
        inside_strings = _lines_ending_inside_a_string(source)
    except (tokenize.TokenError, SyntaxError, IndentationError):
        return None
    lines = source.split("\n")
    tidied = "\n".join(line if number in inside_strings else line.rstrip(" \t")
                       for number, line in enumerate(lines, start=1)).rstrip("\n") + "\n"
    if tidied == source:
        return None
    try:
        unchanged = ast.dump(ast.parse(source)) == ast.dump(ast.parse(tidied))
    except SyntaxError:
        return None
    return tidied if unchanged else None


def _lines_ending_inside_a_string(source: str) -> set[int]:
    """Line numbers whose line break belongs to a multi-line string, so trailing spaces there are data."""
    protected: set[int] = set()
    string_kinds = {tokenize.STRING, getattr(tokenize, "FSTRING_MIDDLE", tokenize.STRING)}
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type in string_kinds and token.end[0] > token.start[0]:
            protected.update(range(token.start[0], token.end[0]))
    return protected


def tidy_edits(root: Path) -> list[FileEdit]:
    """One edit per Python file under `root` that tidying changes without changing the program."""
    root = Path(root).resolve()
    edits = []
    for path in _python_files(root):
        source = path.read_text(encoding="utf-8")
        tidied = tidy_source(source)
        if tidied is not None:
            edits.append(FileEdit(path=path.relative_to(root).as_posix(), kind="write",
                                  new=tidied, old=source))
    return edits


def _python_files(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*.py")):
        if path.is_file() and not _SKIPPED_DIRS.intersection(path.relative_to(root).parts):
            try:
                path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            yield path
