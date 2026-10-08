"""Durable defect IDs: Elegant.md Rule 9, as a small program that follows PEP 8.

A defect ID is one letter for its priority (C critical, H high, M medium,
L low) and a number: `H12`. An ID never changes meaning once published, so the
allocator only ever moves forward. Gaps are not reused: if H3 was deleted, the
next high-priority ID is still one past the highest ever seen.

WHAT THIS IS
    The Python member of a trio. `exemplars/rust` and `exemplars/cpp23` do the
    same job and read the same `exemplars/vectors.txt`, so the three cannot
    quietly disagree.

WHAT IT CANNOT DO
    Persist anything. Callers hand it the IDs that already exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

__all__ = ["Priority", "DefectId", "ParseError", "Allocator", "parse"]

_U64_MAX = 2**64 - 1


class Priority(Enum):
    """How urgent a defect is; the value is the letter used in its ID."""

    CRITICAL = "C"
    HIGH = "H"
    MEDIUM = "M"
    LOW = "L"

    def __lt__(self, other: object) -> bool:
        """Critical sorts before high, high before medium, medium before low."""
        if not isinstance(other, Priority):
            return NotImplemented
        order = "CHML"
        return order.index(self.value) < order.index(other.value)


class ParseError(ValueError):
    """An ID that cannot be read. `kind` names why, so callers can branch on it."""

    def __init__(self, kind: str, text: str) -> None:
        super().__init__(f"{text!r} is not a defect ID: {kind}")
        self.kind = kind


@dataclass(frozen=True, order=True)
class DefectId:
    """A priority and a number of at least one."""

    priority: Priority
    number: int

    def __post_init__(self) -> None:
        if not 1 <= self.number <= _U64_MAX:
            raise ParseError("bad_number", str(self.number))

    def __str__(self) -> str:
        return f"{self.priority.value}{self.number}"


def parse(text: str) -> DefectId:
    """Read an ID such as `H12`; raise ParseError saying exactly what is wrong."""
    if not text:
        raise ParseError("empty", text)
    try:
        priority = Priority(text[0])
    except ValueError:
        raise ParseError("bad_priority", text) from None
    digits = text[1:]
    if not digits.isascii() or not digits.isdigit() or int(digits) == 0 or int(digits) > _U64_MAX:
        raise ParseError("bad_number", text)
    if digits[0] == "0":
        raise ParseError("leading_zero", text)
    return DefectId(priority, int(digits))


class Allocator:
    """Hands out the next unused number for a priority, and never goes backward."""

    def __init__(self, existing: Iterable[str] = ()) -> None:
        self._highest = {priority: 0 for priority in Priority}
        for text in existing:
            known = parse(text)
            self._highest[known.priority] = max(self._highest[known.priority], known.number)

    def allocate(self, priority: Priority) -> DefectId:
        """The next ID for `priority`; it is recorded, so it is never handed out twice."""
        number = self._highest[priority] + 1
        if number > _U64_MAX:
            raise ParseError("bad_number", str(number))
        self._highest[priority] = number
        return DefectId(priority, number)
