"""Where each critic finding comes from, so a reviewer can check it without taking Burnish's word for it.

Every row the claims critic reports carries a `Provenance`: the claim it assessed and where that claim is written, the file
and line of each piece of evidence, the method used, whether the evidence states the fact directly or the verdict rests on
a reading of it, what was not inspected, and the reason for the verdict. With those six things a person can open the same
lines, repeat the same comparison and see whether they reach the same answer.

"direct" means the evidence itself states the fact the verdict rests on (pyproject.toml pins this commit, the parser stopped
at this line, Warden's suite result has failures). "inferred" means a step of reading sits between the evidence and the
verdict that another reader could take differently (which package a module belongs to, which pin a sentence means, whether
a README reads as a brochure). "none" means no evidence could be had in this run, and the verdict says so.

WHAT IT DOES NOT OWN
    Finding anything. It only holds and prints what the critic and the drift checks already found.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

__all__ = ["Basis", "Source", "Provenance", "BASES"]

Basis = Literal["direct", "inferred", "none"]

#: What each basis means, as the printed report states it.
BASES: dict[str, str] = {
    "direct": "direct (the evidence states it)",
    "inferred": "inferred (the verdict rests on a reading of the evidence another reader could make differently)",
    "none": "none (no evidence could be had in this run)",
}


@dataclass(frozen=True)
class Source:
    """A place: a file and a line in it, and what sits there.

    `path` is relative to the tree that was read, or empty when the evidence is not a file (a suite result Warden handed in,
    a count given on the command line). `line` counts from 1; 0 means the whole file, or no line at all.
    """

    path: str = ""
    line: int = 0
    what: str = ""

    def render(self) -> str:
        """"pyproject.toml line 9: git pin cns", "pyproject.toml (whole file): ...", or the description alone."""
        if not self.path:
            return self.what or "not a file"
        where = f"{self.path} line {self.line}" if self.line else f"{self.path} (whole file)"
        return f"{where}: {self.what}" if self.what else where


@dataclass(frozen=True)
class Provenance:
    """The six things a reviewer needs to repeat one finding: claim, evidence, method, basis, what was not read, reason."""

    claim: str
    claim_at: Source
    evidence: tuple[Source, ...]
    method: str
    basis: Basis
    not_inspected: tuple[str, ...]
    reason: str

    def lines(self) -> list[str]:
        """The provenance as indented markdown list items, one per field, to print under the finding."""
        where = self.claim_at.render() if self.claim_at.path or self.claim_at.what else "not written anywhere"
        evidence = "; ".join(s.render() for s in self.evidence) or "none was read or handed in"
        return [
            f"  - Claim: {self.claim} ({where})",
            f"  - Evidence: {evidence}",
            f"  - Method: {self.method}",
            f"  - Evidence is: {BASES[self.basis]}",
            f"  - Not inspected: {'; '.join(self.not_inspected)}",
            f"  - Reason: {self.reason}",
        ]
