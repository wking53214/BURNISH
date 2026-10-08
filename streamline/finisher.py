"""Streamline as Elegant's Finisher: called once, after the loop has converged.

By now Ghost Tools has reported, the Proposer has fixed what it could, and
Elegant has measured the suite. Streamline takes the result and does two
things, as one proposal:

  1. tidies the code (see `streamline.beautify`), behavior-preserving, and
  2. writes the final README: the author's prose kept, the missing required
     sections added from the tree, and CLAIMS VS REALITY replaced with the
     critic's commentary on the measured facts.

Streamline writes nothing. It returns a proposal; Elegant applies it under the
same gate as every other change and puts it back if the suite breaks or Ghost
finds anything new. Streamline counts no tests and detects no defects: what it
says about either, it quotes from the `Facts` Elegant hands it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from elegant.models import FileEdit, Transformation, TransformationStatus
from elegant.roles import Facts

from .beautify import tidy_edits
from .critic import CriticReport, PoetryCritic
from .narrative import inspect_tree
from .readme import finalize_readme
from .readme_critic import ReadmeCritic, ReadmeReport

__all__ = ["Streamline"]


class Streamline:
    """The Finisher: `elegant tagteam --finisher streamline.finisher:Streamline`."""

    def finish(self, target: Path, baseline: str, facts: Facts) -> Optional[Transformation]:
        """One proposal: tidied code and the final README, or None if neither would change."""
        target = Path(target).resolve()
        edits = tidy_edits(target)
        readme = self._readme_edit(target, facts)
        if readme is not None:
            edits.append(readme)
        if not edits:
            return None
        return Transformation(
            target=str(target),
            intent="finish: tidy the code and write the final README with the critic's commentary",
            architectural_reason="The loop has converged; this is the single hand-off to Streamline.",
            affected_files=tuple(e.path for e in edits),
            expected_behavior="Python behavior unchanged (every tidied file parses to the same syntax tree)",
            preservation_requirements=("the target's suite result is unchanged",
                                       "Ghost reports no finding it did not report before"),
            known_defects=facts.remaining,
            transformation_scope="finish",
            baseline_reference=baseline,
            evidence=tuple(d.identity for d in facts.remaining),
            edits=tuple(edits),
            status=TransformationStatus.PROPOSED,
        )

    def _readme_edit(self, target: Path, facts: Facts) -> Optional[FileEdit]:
        narrative = inspect_tree(target)
        report = PoetryCritic().critique(target, narrative, facts)
        commentary = _commentary(report, ReadmeCritic().critique(target))
        path = target / "README.md"
        old = path.read_text(encoding="utf-8") if path.is_file() else ""
        new = finalize_readme(old, narrative, report, commentary, _measured(facts))
        if new == old:
            return None
        return FileEdit(path="README.md", kind="write", new=new, old=old)


def _commentary(report: CriticReport, readme: ReadmeReport) -> str:
    """The critic's words for the README: what is unsupported or unknown, then the README critic's gaps."""
    lines = [f"- Unsupported: {item}" for item in report.unsupported]
    lines += [f"- Unknown: {item}" for item in report.unknown]
    lines += ["" if lines else "", "README critic, on the README as it stood going into the finish:", ""]
    lines += [f"- {gap.render()}" for gap in (*readme.failures, *readme.gaps)] or ["- no failures or gaps"]
    return "\n".join(lines)


def _measured(facts: Facts) -> dict[str, str]:
    """Section text that quotes the suite result Elegant measured, when it ran and was green."""
    suite = facts.suite
    if suite is None or not suite.green:
        return {}
    line = f"- Elegant ran the target's suite at the end of the loop: {suite.describe()}."
    return {"WHAT WORKS": line, "WHAT IS PROVEN": line}
