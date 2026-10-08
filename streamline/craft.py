"""Streamline as a craft: the four answers Elegant asks for.

Elegant governs the change (a human grant, a green suite, SWIZZLE's proofs).
This class supplies what Elegant will not: what is true of the tree now,
whether it is good enough, what single change would improve it, and whether the
change held up. The reviewer and the oracle are separate objects that never
import each other, so a flattering review cannot launder a bad change.

Today the one proposer is the documentation-honesty rewrite. Naming, comments,
guards and function splits are designed (see `docs/CRITERIA.md`) and not built;
`streamline languages` says which are which.
"""

from __future__ import annotations

from pathlib import Path

from elegant.craft import AttackResult, Review
from elegant.models import Defect, Transformation

from .critic import PoetryCritic
from .oracle import GroundTruth, attack_documentation_honesty, freeze
from .proposers import documentation_honesty_proposer

__all__ = ["Streamline"]


class Streamline:
    """A craft for Elegant's tag team: `elegant tagteam --craft streamline.craft:Streamline`."""

    def __init__(self) -> None:
        self._critic = PoetryCritic()

    def freeze(self, target: Path) -> GroundTruth:
        """What is true of the tree before anything is written."""
        return freeze(Path(target))

    def review(self, target: Path) -> Review:
        """Whether the tree's documents tell the truth about the tree."""
        report = self._critic.critique(Path(target))
        return Review(good_enough=report.good_enough, verdict=report.verdict)

    def propose(self, target: Path, observed: tuple[Defect, ...], ground: GroundTruth) -> Transformation:
        """The one change this craft can make today: make a false test count honest."""
        return documentation_honesty_proposer(Path(target), observed, ground)

    def attack(self, target: Path, ground: GroundTruth) -> AttackResult:
        """Re-count the tree and reject any README that still states a wrong test count."""
        return attack_documentation_honesty(Path(target), ground)
