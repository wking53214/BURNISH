"""The six verdict states a claim can reach, and the rule that absence of evidence is never falsity.

A claim moves through the states in order. It is CLAIM_IDENTIFIED when the README states it. It is EVIDENCE_FOUND when
something in the tree or the measurements speaks to it. It ends in one of four states:

  * EVIDENCE_SUPPORTS: what was read agrees with the claim.
  * EVIDENCE_CONTRADICTS: what was read shows the claim is false. Only this state makes the critic FAIL.
  * EVIDENCE_INSUFFICIENT: the claim was checked, and what could be read does not settle it.
  * NOT_CHECKED: the claim was identified, and no check for its shape exists. It is listed, and it changes no outcome.

The trail is the list of states a verdict passed through, so a reader sees whether evidence was found before the end.

WHAT IT DOES NOT OWN
    Deciding a verdict. It holds one and refuses the impossible ones.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ..provenance import Provenance

__all__ = ["State", "FINAL", "Verdict", "verdict_of_row"]


class State(str, Enum):
    """Where a claim stands. The first two are on the way; the last four are where a verdict ends."""

    CLAIM_IDENTIFIED = "CLAIM_IDENTIFIED"
    EVIDENCE_FOUND = "EVIDENCE_FOUND"
    EVIDENCE_SUPPORTS = "EVIDENCE_SUPPORTS"
    EVIDENCE_CONTRADICTS = "EVIDENCE_CONTRADICTS"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"
    NOT_CHECKED = "NOT_CHECKED"


FINAL = frozenset({State.EVIDENCE_SUPPORTS, State.EVIDENCE_CONTRADICTS, State.EVIDENCE_INSUFFICIENT, State.NOT_CHECKED})


@dataclass(frozen=True)
class Verdict:
    """A final state, the trail that led to it, and the provenance that lets a reviewer repeat it."""

    state: State
    provenance: Provenance

    def __post_init__(self) -> None:
        if self.state not in FINAL:
            raise ValueError(f"{self.state.value} is a step on the way, not a verdict")
        if self.state in (State.EVIDENCE_SUPPORTS, State.EVIDENCE_CONTRADICTS) and not self.provenance.evidence:
            raise ValueError(f"{self.state.value} needs evidence that was read; none is recorded")
        if self.state is State.EVIDENCE_CONTRADICTS and self.provenance.basis == "none":
            raise ValueError("absence of evidence is never falsity: a contradiction needs a basis other than none")

    @property
    def trail(self) -> tuple[State, ...]:
        """The states passed through: identified, then found when any evidence was read, then the final state."""
        found = (State.EVIDENCE_FOUND,) if self.provenance.evidence else ()
        return (State.CLAIM_IDENTIFIED,) + found + (self.state,)

    def render(self) -> str:
        """"EVIDENCE_SUPPORTS (CLAIM_IDENTIFIED > EVIDENCE_FOUND > EVIDENCE_SUPPORTS)"."""
        return f"{self.state.value} ({' > '.join(s.value for s in self.trail)})"


_INSUFFICIENT = frozenset({"unmeasured", "unverifiable", "unconfirmed", "unchecked"})


def verdict_of_row(supported: bool, agreement: str, provenance: Optional[Provenance]) -> Optional[Verdict]:
    """The verdict a critic row stands for, read from what the row already says. None for a row with no provenance.

    A supported row is EVIDENCE_SUPPORTS. A row the evidence disagrees with is EVIDENCE_CONTRADICTS. Every other unsupported
    row (a count nothing measured, a broken pyproject.toml, an import inside a function, an absolute nothing backs) was
    checked and not settled: EVIDENCE_INSUFFICIENT.
    """
    if provenance is None:
        return None
    if supported:
        return Verdict(State.EVIDENCE_SUPPORTS, provenance)
    if agreement == "disagrees":
        return Verdict(State.EVIDENCE_CONTRADICTS, provenance)
    return Verdict(State.EVIDENCE_INSUFFICIENT, provenance)
